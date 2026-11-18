import logging
from pathlib import Path
from contextlib import asynccontextmanager

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from app.core.database import engine
from app.api import auth, groups, contributions, loans, meetings, credit_scores

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate()
    yield


app = FastAPI(
    title="ChamaScore API",
    description="Credit Underwriting Platform for Informal Savings Groups",
    version="1.0.0",
    docs_url="/api/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(groups.router, prefix="/api/v1/groups", tags=["Groups"])
app.include_router(contributions.router, prefix="/api/v1/contributions", tags=["Contributions"])
app.include_router(loans.router, prefix="/api/v1/loans", tags=["Loans"])
app.include_router(meetings.router, prefix="/api/v1/meetings", tags=["Meetings"])
app.include_router(credit_scores.router, prefix="/api/v1/credit-scores", tags=["Credit Scores"])

@app.get("/")
async def root():
    return {"message": "ChamaScore API", "version": "1.0.0", "docs": "/api/docs"}

@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/health/live")
async def liveness():
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness():
    alembic_config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            current_revision = MigrationContext.configure(connection).get_current_revision()
        migration_heads = ScriptDirectory.from_config(alembic_config).get_heads()
    except (SQLAlchemyError, CommandError):
        logger.exception("Database readiness check failed")
        raise HTTPException(status_code=503, detail="Database is not ready")

    if current_revision is None or current_revision not in migration_heads:
        raise HTTPException(status_code=503, detail="Database schema is not up to date")
    return {"status": "ready"}