import asyncio
import os
import sys
from datetime import date, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.contributions import list_contributions, record_contribution
from app.api.credit_scores import get_credit_score
from app.api.groups import get_group
from app.api.loans import approve_loan, apply_loan, list_loans
from app.api.meetings import create_meeting, list_meetings
from app.core.database import Base
from app.models.models import Group, GroupMember, Loan, LoanApproval, User
from app.schemas.schemas import ContributionCreate, LoanApplication, MeetingCreate


@pytest.fixture
def loan_context():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()

    users = [
        User(
            id=f"user-{index}",
            email=f"user-{index}@example.com",
            phone=f"07{index:08d}",
            national_id=f"id-{index}",
            full_name=f"Member {index}",
            password_hash="hash",
        )
        for index in range(1, 7)
    ]
    group = Group(
        id="group-1",
        name="Test Group",
        contribution_amount=100,
        meeting_frequency="monthly",
        created_date=date.today(),
        created_by=users[0].id,
    )
    db.add_all([*users, group])
    db.flush()
    db.add_all([
        GroupMember(
            id=f"membership-{index}",
            user_id=users[index - 1].id,
            group_id=group.id,
            joined_date=date.today(),
            is_active=True,
        )
        for index in range(1, 6)
    ])
    loan = Loan(
        id="loan-1",
        group_id=group.id,
        member_id=users[0].id,
        amount=500,
        purpose="Emergency medical costs",
        application_date=date.today(),
        repayment_date=date.today(),
        approval_status="pending",
        status="pending",
    )
    db.add(loan)
    db.commit()

    yield db, users, loan

    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_one_vote_per_member_and_yes_threshold(loan_context):
    db, users, loan = loan_context

    result = asyncio.run(approve_loan(loan.id, False, users[1].id, db))
    assert result["yes_votes"] == 0
    assert result["approval_status"] == "pending"

    with pytest.raises(HTTPException) as duplicate:
        asyncio.run(approve_loan(loan.id, True, users[1].id, db))
    assert duplicate.value.status_code == 409
    db.rollback()

    for voter in users[2:5]:
        result = asyncio.run(approve_loan(loan.id, True, voter.id, db))
        assert result["approval_status"] == "pending"

    result = asyncio.run(approve_loan(loan.id, True, users[0].id, db))
    assert result["yes_votes"] == 4
    assert result["active_members"] == 5
    assert result["approval_status"] == "approved"
    assert db.query(LoanApproval).filter(LoanApproval.loan_id == loan.id).count() == 5
    assert db.query(Loan).filter(Loan.id == loan.id).one().status == "active"


def test_nonmember_cannot_apply_list_or_vote(loan_context):
    db, users, loan = loan_context
    outsider = users[5]
    application = LoanApplication(
        group_id=loan.group_id,
        amount=100,
        purpose="Emergency medical costs",
        repayment_date=date.today(),
    )

    with pytest.raises(HTTPException) as apply_error:
        asyncio.run(apply_loan(application, outsider.id, db))
    assert apply_error.value.status_code == 404
    db.rollback()

    with pytest.raises(HTTPException) as list_error:
        asyncio.run(list_loans(loan.group_id, outsider.id, db))
    assert list_error.value.status_code == 404
    db.rollback()

    with pytest.raises(HTTPException) as vote_error:
        asyncio.run(approve_loan(loan.id, True, outsider.id, db))
    assert vote_error.value.status_code == 404
    db.rollback()
    assert db.query(LoanApproval).filter(LoanApproval.loan_id == loan.id).count() == 0


def test_nonmember_cannot_access_or_write_group_records(loan_context):
    db, users, loan = loan_context
    outsider = users[5]

    protected_reads = [
        get_group(loan.group_id, outsider.id, db),
        list_contributions(loan.group_id, outsider.id, db),
        list_meetings(loan.group_id, outsider.id, db),
        get_credit_score(loan.group_id, outsider.id, db),
    ]
    for request in protected_reads:
        with pytest.raises(HTTPException) as error:
            asyncio.run(request)
        assert error.value.status_code == 404

    contribution = ContributionCreate(
        group_id=loan.group_id,
        member_id=users[0].id,
        amount=100,
        contribution_date=date.today(),
    )
    with pytest.raises(HTTPException) as contribution_error:
        asyncio.run(record_contribution(contribution, outsider.id, db))
    assert contribution_error.value.status_code == 404

    meeting = MeetingCreate(
        group_id=loan.group_id,
        title="Monthly meeting",
        date=datetime.now(),
    )
    with pytest.raises(HTTPException) as meeting_error:
        asyncio.run(create_meeting(meeting, outsider.id, db))
    assert meeting_error.value.status_code == 404
