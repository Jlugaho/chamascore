import asyncio
from datetime import timedelta
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import auth
from app.core.config import Settings
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.models.models import User
from app.schemas.schemas import UserCreate


@pytest.fixture
def api_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine)
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1/auth")

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, test_session

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def registration_payload(**overrides):
    payload = {
        "email": "member@example.com",
        "phone": "0712345678",
        "national_id": "12345678",
        "full_name": "Test Member",
        "password": "SecurePass123",
    }
    payload.update(overrides)
    return payload


def test_registration_login_and_active_user_lookup(api_client):
    client, _ = api_client

    response = client.post("/api/v1/auth/register", json=registration_payload())
    assert response.status_code == 201
    assert "national_id" not in response.json()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "member@example.com", "password": "SecurePass123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "member@example.com"


def test_duplicate_registration_identifiers_are_controlled(api_client):
    client, _ = api_client
    assert client.post(
        "/api/v1/auth/register",
        json=registration_payload(),
    ).status_code == 201

    for duplicate in (
        {"email": "member@example.com", "phone": "0712345679", "national_id": "87654321"},
        {"email": "other@example.com", "phone": "0712345678", "national_id": "87654322"},
        {"email": "other@example.com", "phone": "0712345680", "national_id": "12345678"},
    ):
        response = client.post(
            "/api/v1/auth/register",
            json=registration_payload(**duplicate),
        )
        assert response.status_code == 400


def test_registration_unique_constraint_race_returns_conflict():
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit.side_effect = IntegrityError("insert", {}, Exception("unique"))

    with pytest.raises(HTTPException) as error:
        asyncio.run(auth.register(UserCreate(**registration_payload()), db))

    assert error.value.status_code == 409
    db.rollback.assert_called_once()


def test_authenticated_routes_reject_invalid_expired_and_inactive_user_tokens(api_client):
    client, test_session = api_client
    db = test_session()
    user = User(
        id="active-user",
        email="active@example.com",
        phone="0711111111",
        national_id="11111111",
        full_name="Active Member",
        password_hash="unused",
    )
    inactive_user = User(
        id="inactive-user",
        email="inactive@example.com",
        phone="0722222222",
        national_id="22222222",
        full_name="Inactive Member",
        password_hash="unused",
        is_active=False,
    )
    db.add_all([user, inactive_user])
    db.commit()
    active_user_id = user.id
    inactive_user_id = inactive_user.id
    db.close()

    assert client.get("/api/v1/auth/me").status_code == 401
    invalid = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-token"},
    )
    assert invalid.status_code == 401

    expired_token = create_access_token(
        {"sub": active_user_id},
        expires_delta=timedelta(seconds=-1),
    )
    expired = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert expired.status_code == 401

    inactive_token = create_access_token({"sub": inactive_user_id})
    inactive = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {inactive_token}"},
    )
    assert inactive.status_code == 401


def test_production_settings_reject_default_or_placeholder_secrets():
    settings = Settings()
    settings.APP_ENV = "production"
    settings.DATABASE_URL_CONFIGURED = False
    settings.SECRET_KEY = "a-production-secret-that-is-long-enough"
    with pytest.raises(ValueError, match="DATABASE_URL"):
        settings.validate()

    settings.DATABASE_URL_CONFIGURED = True
    settings.SECRET_KEY = "chamascore-dev-secret"
    with pytest.raises(ValueError, match="SECRET_KEY"):
        settings.validate()

    settings.SECRET_KEY = "a-production-secret-that-is-long-enough"
    settings.validate()
