from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.core.config import settings
from app.main import app


def test_readiness_requires_current_migration(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'readiness.db'}"
    monkeypatch.setattr(settings, "DATABASE_URL", database_url)
    test_engine = create_engine(database_url)

    import app.main as main_module

    monkeypatch.setattr(main_module, "engine", test_engine)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))

    try:
        with TestClient(app) as client:
            assert client.get("/health/live").status_code == 200
            assert client.get("/health/ready").status_code == 503

            command.upgrade(config, "head")

            ready = client.get("/health/ready")
            assert ready.status_code == 200
            assert ready.json() == {"status": "ready"}
    finally:
        test_engine.dispose()
