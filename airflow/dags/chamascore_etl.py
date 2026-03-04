"""
ChamaScore Daily ETL Pipeline
Runs every day at midnight EAT (21:00 UTC)
Recalculates credit scores for all active groups
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

sys.path.insert(0, '/opt/airflow')

default_args = {
    'owner': 'chamascore',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'chamascore_daily_scoring',
    default_args=default_args,
    description='Daily credit score recalculation for all chama groups',
    schedule_interval='0 21 * * *',  # 21:00 UTC = midnight EAT
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['chamascore', 'scoring', 'etl'],
)


def extract_groups(**context):
    """Extract all active groups from the database."""
    import psycopg2
    db_url = os.getenv('CHAMASCORE_DB_URL', 'postgresql://chamascore:pass123@postgres:5432/chamascore')

    # Parse connection string
    import re
    m = re.match(r'postgresql://(\w+):(\w+)@([\w.]+):(\d+)/(\w+)', db_url)
    user, password, host, port, dbname = m.groups()

    conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM groups WHERE is_active = TRUE")
    groups = [{'id': row[0], 'name': row[1]} for row in cur.fetchall()]
    conn.close()

    print(f"✓ Extracted {len(groups)} active groups")
    context['ti'].xcom_push(key='groups', value=groups)
    return groups


def calculate_scores(**context):
    """Calculate credit scores for all extracted groups."""
    import psycopg2
    from sqlalchemy import create_engine, func, text
    from sqlalchemy.orm import sessionmaker

    groups = context['ti'].xcom_pull(key='groups', task_ids='extract_groups')
    if not groups:
        print("No groups to score")
        return []

    db_url = os.getenv('CHAMASCORE_DB_URL', 'postgresql://chamascore:pass123@postgres:5432/chamascore')
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    sys.path.insert(0, '/opt/airflow')
    from app.scoring.heuristic_model import HeuristicCreditScorer, engineer_features_from_raw

    scorer = HeuristicCreditScorer()
    results = []

    for group in groups:
        try:
            # Get raw metrics
            from datetime import date, timedelta
            today = date.today()

            row = db.execute(text("""
                SELECT
                    g.created_date,
                    g.contribution_amount,
                    COUNT(DISTINCT CASE WHEN gm.is_active THEN gm.user_id END) as active_members,
                    COUNT(DISTINCT gm.user_id) as total_members,
                    COALESCE(SUM(c.amount), 0) as total_contributions,
                    COALESCE(AVG(c.amount), 0) as avg_contribution,
                    COUNT(DISTINCT CASE WHEN l.status = 'repaid' THEN l.id END) as repaid_loans,
                    COUNT(DISTINCT CASE WHEN l.status = 'defaulted' THEN l.id END) as defaulted_loans,
                    COALESCE(SUM(CASE WHEN l.status = 'active' THEN l.amount ELSE 0 END), 0) as active_loans_total,
                    COUNT(DISTINCT m.id) as meetings_30d
                FROM groups g
                LEFT JOIN group_members gm ON g.id = gm.group_id
                LEFT JOIN contributions c ON g.id = c.group_id
                LEFT JOIN loans l ON g.id = l.group_id
                LEFT JOIN meetings m ON g.id = m.group_id
                    AND m.date >= :thirty_days_ago
                WHERE g.id = :group_id
                GROUP BY g.id, g.created_date, g.contribution_amount
            """), {'group_id': group['id'], 'thirty_days_ago': today - timedelta(days=30)}).fetchone()

            if not row:
                continue

            raw = {
                'group_age_days': (today - row[0]).days if row[0] else 0,
                'contribution_amount': float(row[1] or 0),
                'active_members': row[2] or 1,
                'total_ever_members': row[3] or 1,
                'total_contributions': float(row[4] or 0),
                'avg_contribution': float(row[5] or 0),
                'stddev_contribution': 0,
                'repaid_loans_count': row[6] or 0,
                'defaulted_loans_count': row[7] or 0,
                'total_savings': float(row[4] or 0),
                'active_loans_total': float(row[8] or 0),
                'meetings_held_30d': row[9] or 0,
                'actual_attendance_30d': (row[9] or 0) * (row[2] or 1),
                'loans_disbursed_90d': 0,
                'defaults_90d': 0,
            }

            features = engineer_features_from_raw(raw)
            score, breakdown = scorer.calculate_score(features)
            band = scorer.get_score_band(score)
            recs = scorer.generate_recommendations(breakdown)

            results.append({
                'group_id': group['id'],
                'group_name': group['name'],
                'score': score,
                'band': band,
                'recommendations': recs,
            })

            print(f"  ✓ {group['name']}: {score} ({band})")

        except Exception as e:
            print(f"  ✗ Error scoring {group['name']}: {e}")

    db.close()
    context['ti'].xcom_push(key='scores', value=results)
    return results


def load_scores(**context):
    """Save scores back to the database."""
    import psycopg2
    from datetime import date
    import uuid

    scores = context['ti'].xcom_pull(key='scores', task_ids='calculate_scores')
    if not scores:
        print("No scores to save")
        return

    db_url = os.getenv('CHAMASCORE_DB_URL', 'postgresql://chamascore:pass123@postgres:5432/chamascore')
    m = __import__('re').match(r'postgresql://(\w+):(\w+)@([\w.]+):(\d+)/(\w+)', db_url)
    user, password, host, port, dbname = m.groups()

    conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
    cur = conn.cursor()

    today = date.today()
    saved = 0

    for s in scores:
        import json
        cur.execute("""
            INSERT INTO credit_scores (id, group_id, score_date, score_value, score_band, features_json, calculation_log)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (group_id, score_date) DO UPDATE
            SET score_value = EXCLUDED.score_value,
                score_band = EXCLUDED.score_band,
                features_json = EXCLUDED.features_json
        """, (
            str(uuid.uuid4()),
            s['group_id'],
            today,
            s['score'],
            s['band'],
            json.dumps({'recommendations': s['recommendations']}),
            f"ETL run: {datetime.now().isoformat()}"
        ))
        saved += 1

    conn.commit()
    conn.close()
    print(f"✓ Saved {saved} scores to database")


def send_summary(**context):
    """Print a summary of the ETL run."""
    scores = context['ti'].xcom_pull(key='scores', task_ids='calculate_scores')
    print("\n" + "=" * 50)
    print(f"CHAMASCORE ETL SUMMARY — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    if scores:
        for s in scores:
            print(f"  {s['group_name']:<35} {s['score']} ({s['band']})")
    print(f"\nTotal groups scored: {len(scores) if scores else 0}")
    print("=" * 50)


# Define tasks
t1 = PythonOperator(task_id='extract_groups', python_callable=extract_groups, dag=dag)
t2 = PythonOperator(task_id='calculate_scores', python_callable=calculate_scores, dag=dag)
t3 = PythonOperator(task_id='load_scores', python_callable=load_scores, dag=dag)
t4 = PythonOperator(task_id='send_summary', python_callable=send_summary, dag=dag)

# Pipeline: extract → score → load → summary
t1 >> t2 >> t3 >> t4