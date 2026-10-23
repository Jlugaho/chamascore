from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import case, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from datetime import date, timedelta
from math import sqrt
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import Group, Contribution, Loan, Meeting, MeetingAttendance, GroupMember, CreditScore
from app.api.dependencies import require_active_group_member
from app.schemas.schemas import CreditScoreOut, FeatureDetail
from app.scoring.heuristic_model import HeuristicCreditScorer, engineer_features_from_raw
import uuid

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
    contribution_count = 0
    contribution_mean = 0.0
    squared_deviation_sum = 0.0
    for (amount,) in db.query(Contribution.amount).filter(
        Contribution.group_id == group_id
    ).yield_per(1000):
        contribution_count += 1
        value = float(amount)
        delta = value - contribution_mean
        contribution_mean += delta / contribution_count
        squared_deviation_sum += delta * (value - contribution_mean)
    contribution_stddev = (
        sqrt(squared_deviation_sum / contribution_count)
        if contribution_count >= 2 else None
    )

    active_members = db.query(GroupMember).filter(GroupMember.group_id == group_id, GroupMember.is_active == True).count()
    total_members = db.query(GroupMember).filter(GroupMember.group_id == group_id).count()

    repaid = db.query(Loan).filter(Loan.group_id == group_id, Loan.status == "repaid").count()
    defaulted = db.query(Loan).filter(Loan.group_id == group_id, Loan.status == "defaulted").count()
    active_loans_total = db.query(func.sum(Loan.amount)).filter(Loan.group_id == group_id, Loan.status == "active").scalar() or 0

    ninety_days_ago = today - timedelta(days=90)
    loans_90d = db.query(Loan).filter(Loan.group_id == group_id, Loan.application_date >= ninety_days_ago).count()
    defaults_90d = db.query(Loan).filter(Loan.group_id == group_id, Loan.status == "defaulted", Loan.application_date >= ninety_days_ago).count()

    thirty_days_ago = today - timedelta(days=30)
    attendance_stats = db.query(
        func.count(MeetingAttendance.id),
        func.sum(case((MeetingAttendance.attended.is_(True), 1), else_=0)),
    ).join(Meeting, Meeting.id == MeetingAttendance.meeting_id).filter(
        Meeting.group_id == group_id,
        Meeting.date >= thirty_days_ago,
    ).first()
    attendance_records = attendance_stats[0] or 0
    actual_attendance = attendance_stats[1] or 0
    meetings_30d = db.query(Meeting).filter(Meeting.group_id == group_id, Meeting.date >= thirty_days_ago).count()

    return {
        "group_age_days": age_days,
        "avg_contribution": float(contrib_stats[1] or 0),
        "stddev_contribution": contribution_stddev,
        "contribution_count": contribution_count,
        "total_contributions": float(contrib_stats[0] or 0),
        "active_members": active_members,
        "total_ever_members": total_members,
        "contribution_amount": float(group.contribution_amount),
        "repaid_loans_count": repaid,
        "defaulted_loans_count": defaulted,
        "total_savings": float(contrib_stats[0] or 0),
        "active_loans_total": float(active_loans_total),
        "meetings_held_30d": meetings_30d,
        "attendance_records_30d": attendance_records,
        "actual_attendance_30d": actual_attendance,
        "loans_disbursed_90d": loans_90d,
        "defaults_90d": defaults_90d,
    }

@router.get("/group/{group_id}", response_model=CreditScoreOut)
async def get_credit_score(group_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    require_active_group_member(group_id, user_id, db)
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    raw = get_raw_data(group_id, db)
    features = engineer_features_from_raw(raw)
    score, breakdown = scorer.calculate_score(features)
    band = scorer.get_score_band(score)
    recommendations = scorer.generate_recommendations(breakdown)
    log = scorer.generate_calculation_log(features, breakdown, score)

    features_json = {
        k: {
            "value": v.value,
            "rating": v.rating,
            "available": v.available,
            "availability_note": v.availability_note,
        }
        for k, v in breakdown.items()
    }

    # Upsert — insert or update if today's score already exists
    score_values = dict(
        id=str(uuid.uuid4()),
        group_id=group_id,
        score_date=date.today(),
        score_value=score,
        score_band=band,
        features_json=features_json,
        calculation_log=log,
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
            score_value=score,
            score_band=band,
            features_json=features_json,
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
            for k, v in breakdown.items()
        },
        recommendations=recommendations,
        calculation_log=log,
    )