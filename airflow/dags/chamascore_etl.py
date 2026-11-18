"""
ChamaScore Daily ETL Pipeline
Runs every day at midnight EAT (21:00 UTC)
Recalculates credit scores for all active groups
"""
from datetime import date, datetime, timedelta
import logging
import os
import sys
import uuid

from airflow import DAG
from airflow.operators.python import PythonOperator

if "/opt/airflow" not in sys.path:
    sys.path.insert(0, "/opt/airflow")

default_args = {
    "owner": "chamascore",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "chamascore_daily_scoring",
    default_args=default_args,
    description="Daily credit score recalculation for all chama groups",
    schedule_interval="0 21 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["chamascore", "scoring", "etl"],
)

logger = logging.getLogger(__name__)


def _create_db_engine():
    from sqlalchemy import create_engine

    db_url = os.getenv("CHAMASCORE_DB_URL")
    if not db_url:
        raise RuntimeError("CHAMASCORE_DB_URL must be configured for the scoring DAG")
    return create_engine(db_url, pool_pre_ping=True)


def extract_groups(**context):
    """Extract all active groups from the database."""
    from sqlalchemy.orm import sessionmaker

    from app.models.models import Group

    engine = _create_db_engine()
    try:
        with sessionmaker(bind=engine)() as db:
            groups = [
                {"id": group.id, "name": group.name}
                for group in db.query(Group.id, Group.name).filter(Group.is_active.is_(True)).all()
            ]
    finally:
        engine.dispose()

    logger.info("Extracted %d active groups", len(groups))
    context["ti"].xcom_push(key="groups", value=groups)
    return groups


def calculate_scores(**context):
    """Calculate credit scores using the API's shared data and scoring logic."""
    from sqlalchemy.orm import sessionmaker

    from app.scoring.data import get_raw_group_data
    from app.scoring.heuristic_model import HeuristicCreditScorer, score_from_raw

    groups = context["ti"].xcom_pull(key="groups", task_ids="extract_groups")
    if not groups:
        logger.info("No active groups to score")
        return []

    engine = _create_db_engine()
    scorer = HeuristicCreditScorer()
    today = date.today()
    results = []
    try:
        with sessionmaker(bind=engine)() as db:
            for group in groups:
                raw = get_raw_group_data(group["id"], db, today)
                if raw is None:
                    logger.warning("Skipping missing group %s", group["id"])
                    continue
                calculation = score_from_raw(raw, scorer)
                results.append({
                    "group_id": group["id"],
                    "group_name": group["name"],
                    "score_date": today.isoformat(),
                    "score": calculation.score,
                    "band": calculation.band,
                    "features_json": calculation.features_json,
                    "calculation_log": calculation.calculation_log,
                    "recommendations": calculation.recommendations,
                })
                logger.info("%s: %s (%s)", group["name"], calculation.score, calculation.band)
    finally:
        engine.dispose()

    context["ti"].xcom_push(key="scores", value=results)
    return results


def load_scores(**context):
    """Persist the same score breakdown and log exposed by the API."""
    from sqlalchemy.dialects.postgresql import insert

    from app.models.models import CreditScore

    scores = context["ti"].xcom_pull(key="scores", task_ids="calculate_scores")
    if not scores:
        logger.info("No scores to save")
        return

    rows = [
        {
            "id": str(uuid.uuid4()),
            "group_id": score["group_id"],
            "score_date": date.fromisoformat(score["score_date"]),
            "score_value": score["score"],
            "score_band": score["band"],
            "features_json": score["features_json"],
            "calculation_log": score["calculation_log"],
        }
        for score in scores
    ]
    statement = insert(CreditScore).values(rows)
    statement = statement.on_conflict_do_update(
        index_elements=[CreditScore.group_id, CreditScore.score_date],
        set_={
            "score_value": statement.excluded.score_value,
            "score_band": statement.excluded.score_band,
            "features_json": statement.excluded.features_json,
            "calculation_log": statement.excluded.calculation_log,
        },
    )

    engine = _create_db_engine()
    try:
        with engine.begin() as connection:
            connection.execute(statement)
    finally:
        engine.dispose()
    logger.info("Saved %d group scores", len(rows))


def send_summary(**context):
    """Log the completed scoring run."""
    scores = context["ti"].xcom_pull(key="scores", task_ids="calculate_scores")
    logger.info("CHAMASCORE ETL SUMMARY — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    if scores:
        for score in scores:
            logger.info("%s: %s (%s)", score["group_name"], score["score"], score["band"])
    logger.info("Total groups scored: %d", len(scores) if scores else 0)


extract_task = PythonOperator(
    task_id="extract_groups",
    python_callable=extract_groups,
    dag=dag,
)
calculate_task = PythonOperator(
    task_id="calculate_scores",
    python_callable=calculate_scores,
    dag=dag,
)
load_task = PythonOperator(
    task_id="load_scores",
    python_callable=load_scores,
    dag=dag,
)
summary_task = PythonOperator(
    task_id="send_summary",
    python_callable=send_summary,
    dag=dag,
)

extract_task >> calculate_task >> load_task >> summary_task
