from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import date, timedelta
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Group, Contribution, Loan, Meeting, MeetingAttendance, GroupMember, CreditScore
from app.schemas.schemas import CreditScoreOut, FeatureDetail
from app.scoring.heuristic_model import HeuristicCreditScorer, engineer_features_from_raw
import uuid, json

router = APIRouter()
scorer = HeuristicCreditScorer()

def get_raw_data(group_id: str, db: Session) -> dict:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        return None

    today = date.today()
    age_days = (today - group.created_date).days

    contrib_stats = db.query(
        func.sum(Contribution.amount),
        func.avg(Contribution.amount),
        func.count(Contribution.id)
    ).filter(Contribution.group_id == group_id).first()

    active_members = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.is_active == True).count()
    total_members = db.query(GroupMember).filter(GroupMember.group_id == group_id).count()

    repaid = db.query(Loan).filter(Loan.group_id == group_id, Loan.status == "repaid").count()
    defaulted = db.query(Loan).filter(Loan.group_id == group_id, Loan.status == "defaulted").count()
    active_loans_total = db.query(func.sum(Loan.amount)).filter(Loan.group_id == group_id, Loan.status == "active").scalar() or 0

    ninety_days_ago = today - timedelta(days=90)
    loans_90d = db.query(Loan).filter(Loan.group_id == group_id, Loan.application_date >= ninety_days_ago).count()
    defaults_90d = db.query(Loan).filter(Loan.group_id == group_id, Loan.status == "defaulted", Loan.application_date >= ninety_days_ago).count()

    thirty_days_ago = today - timedelta(days=30)
    meetings_30d = db.query(Meeting).filter(Meeting.group_id == group_id, Meeting.date >= thirty_days_ago).count()

    return {
        "group_age_days": age_days,
        "avg_contribution": float(contrib_stats[1] or 0),
        "stddev_contribution": 0,
        "total_contributions": float(contrib_stats[0] or 0),
        "active_members": active_members,
        "total_ever_members": total_members or 1,
        "contribution_amount": float(group.contribution_amount),
        "repaid_loans_count": repaid,
        "defaulted_loans_count": defaulted,
        "total_savings": float(contrib_stats[0] or 0),
        "active_loans_total": float(active_loans_total),
        "meetings_held_30d": meetings_30d,
        "actual_attendance_30d": meetings_30d * active_members,
        "loans_disbursed_90d": loans_90d,
        "defaults_90d": defaults_90d,
    }

@router.get("/group/{group_id}", response_model=CreditScoreOut)
async def get_credit_score(group_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    raw = get_raw_data(group_id, db)
    features = engineer_features_from_raw(raw)
    score, breakdown = scorer.calculate_score(features)
    band = scorer.get_score_band(score)
    recommendations = scorer.generate_recommendations(breakdown)
    log = scorer.generate_calculation_log(features, breakdown, score)

    features_json = {k: {"value": v.value, "rating": v.rating} for k, v in breakdown.items()}

    # Upsert — insert or update if today's score already exists
    stmt = pg_insert(CreditScore).values(
        id=str(uuid.uuid4()),
        group_id=group_id,
        score_date=date.today(),
        score_value=score,
        score_band=band,
        features_json=json.dumps(features_json),
        calculation_log=log,
    ).on_conflict_do_update(
        constraint='uq_group_score_date',
        set_=dict(
            score_value=score,
            score_band=band,
            features_json=json.dumps(features_json),
            calculation_log=log,
        )
    )
    db.execute(stmt)
    db.commit()

    return CreditScoreOut(
        group_id=group_id,
        group_name=group.name,
        score_date=date.today(),
        score_value=score,
        score_band=band,
        features={k: FeatureDetail(value=v.value, unit=v.unit, weight=v.weight, normalized_score=v.normalized_score, contribution=v.contribution, rating=v.rating) for k, v in breakdown.items()},
        recommendations=recommendations,
        calculation_log=log,
    )