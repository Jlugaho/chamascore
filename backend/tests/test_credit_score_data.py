import asyncio
import os
import sys
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.credit_scores import get_credit_score, get_raw_data
from app.core.database import Base
from app.models.models import (
    Contribution,
    Group,
    GroupMember,
    Meeting,
    MeetingAttendance,
    CreditScore,
    User,
)
from app.scoring.heuristic_model import engineer_features_from_raw


def test_raw_score_metrics_use_contribution_variability_and_recorded_attendance():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    try:
        users = [
            User(
                id=f"data-user-{index}",
                email=f"data-user-{index}@example.com",
                phone=f"071{index:07d}",
                national_id=f"data-id-{index}",
                full_name=f"Member {index}",
                password_hash="hash",
            )
            for index in range(1, 3)
        ]
        group = Group(
            id="data-group",
            name="Data Group",
            contribution_amount=200,
            meeting_frequency="monthly",
            created_date=date.today() - timedelta(days=365),
            created_by=users[0].id,
        )
        db.add_all([*users, group])
        db.flush()
        db.add_all([
            GroupMember(
                id=f"data-membership-{index}",
                user_id=user.id,
                group_id=group.id,
                joined_date=date.today(),
                is_active=True,
            )
            for index, user in enumerate(users, start=1)
        ])
        db.add_all([
            Contribution(
                id="contribution-1",
                group_id=group.id,
                member_id=users[0].id,
                amount=100,
                contribution_date=date.today(),
            ),
            Contribution(
                id="contribution-2",
                group_id=group.id,
                member_id=users[1].id,
                amount=300,
                contribution_date=date.today(),
            ),
        ])
        meeting = Meeting(
            id="data-meeting",
            group_id=group.id,
            title="Monthly meeting",
            date=datetime.now(),
        )
        db.add(meeting)
        db.flush()
        db.add_all([
            MeetingAttendance(
                id="attendance-present",
                meeting_id=meeting.id,
                member_id=users[0].id,
                attended=True,
            ),
            MeetingAttendance(
                id="attendance-absent",
                meeting_id=meeting.id,
                member_id=users[1].id,
                attended=False,
            ),
        ])
        db.commit()

        raw = get_raw_data(group.id, db)
        features = engineer_features_from_raw(raw)

        assert raw["contribution_count"] == 2
        assert raw["stddev_contribution"] == 100
        assert raw["attendance_records_30d"] == 2
        assert raw["actual_attendance_30d"] == 1
        assert features["contribution_cv"] == 0.5
        assert features["attendance_rate"] == 0.5

        score = asyncio.run(get_credit_score(group.id, users[0].id, db))
        assert score.features["repayment_rate"].value is None
        assert score.features["repayment_rate"].available is False
        assert score.features["liquidity_ratio"].available is False

        asyncio.run(get_credit_score(group.id, users[0].id, db))
        assert db.query(CreditScore).filter(CreditScore.group_id == group.id).count() == 1
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
