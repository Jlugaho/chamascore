from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine
from app.api import auth, groups, contributions, loans, meetings, credit_scores

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ChamaScore API",
    description="Credit Underwriting Platform for Informal Savings Groups",
    version="1.0.0",
    docs_url="/api/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
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