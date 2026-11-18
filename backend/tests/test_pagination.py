from datetime import date, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import contributions, groups, loans, meetings
from app.core.database import Base, get_db
from app.core.security import get_current_user_id
from app.models.models import Contribution, Group, GroupMember, Loan, Meeting, User


def test_list_endpoints_support_bounded_stable_pagination():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine)
    db = test_session()
    user = User(
        id="pagination-user",
        email="pagination@example.com",
        phone="0712345678",
        national_id="12345678",
        full_name="Pagination User",
        password_hash="unused",
    )
    group = Group(
        id="pagination-group",
        name="Pagination Group",
        contribution_amount=100,
        meeting_frequency="monthly",
        created_date=date.today(),
        created_by=user.id,
    )
    db.add_all([user, group])
    db.flush()
    db.add(GroupMember(
        id="pagination-membership",
        group_id=group.id,
        user_id=user.id,
        joined_date=date.today(),
    ))
    db.add_all([
        Contribution(
            id=f"contribution-{suffix}",
            group_id=group.id,
            member_id=user.id,
            amount=100,
            contribution_date=date(2026, 1, 1),
        )
        for suffix in ("a", "b", "c")
    ])
    db.add_all([
        Loan(
            id=f"loan-{suffix}",
            group_id=group.id,
            member_id=user.id,
            amount=100,
            purpose="Test loan",
            application_date=date(2026, 1, 1),
            approval_status="pending",
            status="pending",
            interest_rate=10,
        )
        for suffix in ("a", "b", "c")
    ])
    db.add_all([
        Meeting(
            id=f"meeting-{suffix}",
            group_id=group.id,
            title=f"Meeting {suffix}",
            date=datetime(2026, 1, 1),
        )
        for suffix in ("a", "b", "c")
    ])
    db.commit()
    group_id = group.id
    db.close()

    app = FastAPI()
    app.include_router(groups.router, prefix="/api/v1/groups")
    app.include_router(contributions.router, prefix="/api/v1/contributions")
    app.include_router(loans.router, prefix="/api/v1/loans")
    app.include_router(meetings.router, prefix="/api/v1/meetings")

    def override_get_db():
        session = test_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: "pagination-user"

    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/groups?limit=1").json()[0]["id"] == group_id
            assert client.get(
                f"/api/v1/contributions/group/{group_id}?limit=1&offset=1"
            ).json()[0]["id"] == "contribution-b"
            assert client.get(
                f"/api/v1/loans/group/{group_id}?limit=1&offset=1"
            ).json()[0]["id"] == "loan-b"
            assert client.get(
                f"/api/v1/meetings/group/{group_id}?limit=1&offset=1"
            ).json()[0]["id"] == "meeting-b"
            assert client.get("/api/v1/groups?limit=501").status_code == 422
            assert client.get("/api/v1/groups?offset=-1").status_code == 422
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
