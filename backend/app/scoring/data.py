from datetime import date, timedelta
from math import sqrt
from typing import Any

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.models import (
    Contribution,
    Group,
    GroupMember,
    Loan,
    Meeting,
    MeetingAttendance,
)


def get_raw_group_data(
    group_id: str,
    db: Session,
    as_of_date: date | None = None,
) -> dict[str, Any] | None:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        return None

    today = as_of_date or date.today()
    age_days = (today - group.created_date).days
    contrib_stats = db.query(
        func.sum(Contribution.amount),
        func.avg(Contribution.amount),
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

    active_members = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.is_active.is_(True),
    ).count()
    total_members = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
    ).count()
    repaid = db.query(Loan).filter(
        Loan.group_id == group_id,
        Loan.status == "repaid",
    ).count()
    defaulted = db.query(Loan).filter(
        Loan.group_id == group_id,
        Loan.status == "defaulted",
    ).count()
    active_loans_total = db.query(func.sum(Loan.amount)).filter(
        Loan.group_id == group_id,
        Loan.status == "active",
    ).scalar() or 0

    ninety_days_ago = today - timedelta(days=90)
    loans_90d = db.query(Loan).filter(
        Loan.group_id == group_id,
        Loan.application_date >= ninety_days_ago,
    ).count()
    defaults_90d = db.query(Loan).filter(
        Loan.group_id == group_id,
        Loan.status == "defaulted",
        Loan.application_date >= ninety_days_ago,
    ).count()

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
    meetings_30d = db.query(Meeting).filter(
        Meeting.group_id == group_id,
        Meeting.date >= thirty_days_ago,
    ).count()

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
