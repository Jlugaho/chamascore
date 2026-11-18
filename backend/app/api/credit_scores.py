from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from datetime import date
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Group, CreditScore
from app.api.dependencies import require_active_group_member
from app.schemas.schemas import CreditScoreOut, FeatureDetail
from app.scoring.data import get_raw_group_data
from app.scoring.heuristic_model import HeuristicCreditScorer, score_from_raw
import uuid

router = APIRouter()
scorer = HeuristicCreditScorer()

def get_raw_data(group_id: str, db: Session, as_of_date: date | None = None) -> dict | None:
    return get_raw_group_data(group_id, db, as_of_date)

@router.get("/group/{group_id}", response_model=CreditScoreOut)
async def get_credit_score(group_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    require_active_group_member(group_id, user_id, db)
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    score_date = date.today()
    raw = get_raw_data(group_id, db, score_date)
    calculation = score_from_raw(raw, scorer)

    # Upsert — insert or update if today's score already exists
    score_values = dict(
        id=str(uuid.uuid4()),
        group_id=group_id,
        score_date=score_date,
        score_value=calculation.score,
        score_band=calculation.band,
        features_json=calculation.features_json,
        calculation_log=calculation.calculation_log,
    )
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        insert_score = pg_insert(CreditScore)
    elif dialect == "sqlite":
        insert_score = sqlite_insert(CreditScore)
    else:
        raise RuntimeError(f"Credit score upsert is not supported for database dialect {dialect}")
    stmt = insert_score.values(**score_values).on_conflict_do_update(
        index_elements=[CreditScore.group_id, CreditScore.score_date],
        set_=dict(
            score_value=calculation.score,
            score_band=calculation.band,
            features_json=calculation.features_json,
            calculation_log=calculation.calculation_log,
        )
    )
    db.execute(stmt)
    db.commit()

    return CreditScoreOut(
        group_id=group_id,
        group_name=group.name,
        score_date=score_date,
        score_value=calculation.score,
        score_band=calculation.band,
        features={
            k: FeatureDetail(
                value=v.value,
                unit=v.unit,
                weight=v.weight,
                normalized_score=v.normalized_score,
                contribution=v.contribution,
                rating=v.rating,
                available=v.available,
                availability_note=v.availability_note,
            )
            for k, v in calculation.breakdown.items()
        },
        recommendations=calculation.recommendations,
        calculation_log=calculation.calculation_log,
    )