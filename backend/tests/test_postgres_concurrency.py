import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.loans import approve_loan
from app.core.database import Base
from app.models.models import Group, GroupMember, Loan, User


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL is required for PostgreSQL concurrency tests",
)


def test_postgres_serializes_distinct_and_duplicate_votes():
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine)
    group_id = str(uuid.uuid4())
    loan_id = str(uuid.uuid4())
    users = [
        User(
            id=str(uuid.uuid4()),
            email=f"{uuid.uuid4()}@example.com",
            phone=f"07{index:08d}",
            national_id=f"{index:08d}",
            full_name=f"Member {index}",
            password_hash="unused",
        )
        for index in range(1, 6)
    ]
    user_ids = [user.id for user in users]
    group = Group(
        id=group_id,
        name="Concurrent Votes",
        contribution_amount=100,
        meeting_frequency="monthly",
        created_date=date.today(),
        created_by=user_ids[0],
    )
    with test_session() as db:
        db.add_all([*users, group])
        db.commit()
        db.add_all([
            GroupMember(
                id=str(uuid.uuid4()),
                user_id=user_id,
                group_id=group_id,
                joined_date=date.today(),
            )
            for user_id in user_ids
        ])
        db.commit()
        db.add(
            Loan(
                id=loan_id,
                group_id=group_id,
                member_id=user_ids[0],
                amount=500,
                application_date=date.today(),
                repayment_date=date.today(),
            )
        )
        db.commit()

    try:
        distinct_barrier = Barrier(4)

        def cast_vote(voter_id):
            distinct_barrier.wait(timeout=10)
            with test_session() as db:
                return asyncio.run(approve_loan(loan_id, True, voter_id, db))

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(cast_vote, user_ids[:4]))

        assert sorted(result["yes_votes"] for result in results) == [1, 2, 3, 4]
        with test_session() as db:
            assert db.query(Loan).filter(Loan.id == loan_id).one().approval_status == "approved"

        duplicate_loan_id = str(uuid.uuid4())
        with test_session() as db:
            db.add(
                Loan(
                    id=duplicate_loan_id,
                    group_id=group_id,
                    member_id=user_ids[0],
                    amount=250,
                    application_date=date.today(),
                    repayment_date=date.today(),
                )
            )
            db.commit()

        duplicate_barrier = Barrier(2)

        def cast_duplicate_vote():
            duplicate_barrier.wait(timeout=10)
            with test_session() as db:
                return asyncio.run(approve_loan(duplicate_loan_id, True, user_ids[1], db))

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(cast_duplicate_vote) for _ in range(2)]
            outcomes = []
            for future in futures:
                try:
                    outcomes.append(future.result(timeout=30))
                except HTTPException as exc:
                    outcomes.append(exc.status_code)

        assert sum(isinstance(outcome, dict) for outcome in outcomes) == 1
        assert outcomes.count(409) == 1
        with test_session() as db:
            assert db.query(Loan).filter(Loan.id == duplicate_loan_id).one().approval_status == "pending"
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
