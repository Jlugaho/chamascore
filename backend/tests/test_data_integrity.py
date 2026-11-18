from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.models import (
    Contribution,
    Group,
    GroupMember,
    Loan,
    Meeting,
    MeetingAttendance,
    User,
)


@pytest.fixture
def integrity_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    users = [
        User(
            id=f"integrity-user-{index}",
            email=f"integrity-{index}@example.com",
            phone=f"073{index:07d}",
            national_id=f"integrity-id-{index}",
            full_name=f"Member {index}",
            password_hash="hash",
        )
        for index in (1, 2)
    ]
    groups = [
        Group(
            id=f"integrity-group-{index}",
            name=f"Integrity Group {index}",
            contribution_amount=100,
            meeting_frequency="monthly",
            created_date=date.today(),
            created_by=users[0].id,
        )
        for index in (1, 2)
    ]
    memberships = [
        GroupMember(
            id=f"integrity-membership-{index}",
            user_id=users[index - 1].id,
            group_id=groups[index - 1].id,
            joined_date=date.today(),
        )
        for index in (1, 2)
    ]
    db.add_all([*users, *groups, *memberships])
    db.commit()
    yield db, users, groups
    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_membership_is_unique_per_group(integrity_db):
    db, users, groups = integrity_db
    db.add(
        GroupMember(
            id="duplicate-membership",
            user_id=users[0].id,
            group_id=groups[0].id,
            joined_date=date.today(),
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


@pytest.mark.parametrize("record_type", ["contribution", "loan"])
def test_financial_record_member_must_belong_to_same_group(integrity_db, record_type):
    db, users, groups = integrity_db
    if record_type == "contribution":
        record = Contribution(
            id="cross-group-contribution",
            group_id=groups[0].id,
            member_id=users[1].id,
            amount=100,
            contribution_date=date.today(),
        )
    else:
        record = Loan(
            id="cross-group-loan",
            group_id=groups[0].id,
            member_id=users[1].id,
            amount=100,
            application_date=date.today(),
            repayment_date=date.today(),
        )
    db.add(record)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_member_can_only_have_one_attendance_record_per_meeting(integrity_db):
    db, users, groups = integrity_db
    meeting = Meeting(
        id="integrity-meeting",
        group_id=groups[0].id,
        title="Monthly meeting",
        date=datetime.now(),
    )
    db.add(meeting)
    db.flush()
    db.add(
        MeetingAttendance(
            id="attendance-first",
            meeting_id=meeting.id,
            member_id=users[0].id,
            attended=True,
        )
    )
    db.commit()

    db.add(
        MeetingAttendance(
            id="attendance-duplicate",
            meeting_id=meeting.id,
            member_id=users[0].id,
            attended=False,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
