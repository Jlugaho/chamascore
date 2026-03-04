# ChamaScore 🏦

> AI-powered credit underwriting platform for Kenyan informal savings groups (chamas)

ChamaScore brings transparent, explainable credit scoring to the 300,000+ chamas operating across Kenya — groups traditionally excluded from formal financial services due to lack of credit history.

---

## The Problem

Kenyan chamas collectively manage over KES 300 billion in assets, yet most cannot access formal credit because banks lack tools to evaluate their creditworthiness. ChamaScore bridges this gap with a transparent, data-driven scoring engine built specifically for chama financial behavior.

---

## Solution

A full-stack platform that:
- Ingests chama financial data (contributions, loans, meetings, attendance)
- Calculates a credit score (300–850) using a transparent heuristic model
- Provides explainable feature breakdowns and actionable recommendations
- Automates daily score recalculation via an Airflow ETL pipeline

---

## Credit Scoring Model

ChamaScore uses a weighted heuristic model with 8 features:

| Feature | Weight | Description |
|---------|--------|-------------|
| Loan Repayment Rate | 25% | Proportion of loans repaid vs defaulted |
| Contribution Consistency | 20% | Coefficient of variation in contributions |
| Group Longevity | 15% | Months since group formation |
| Contribution Reliability | 15% | Actual vs expected contributions |
| Liquidity Ratio | 10% | Savings relative to outstanding loans |
| Member Stability | 5% | Active vs total ever members |
| Attendance Rate | 5% | Meeting attendance last 30 days |
| Recent Default Rate | 5% | Defaults in last 90 days |

**Score Bands:**
- 750–850: Excellent
- 660–749: Very Good
- 600–659: Good
- 500–599: Fair
- 300–499: Poor

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript, Recharts |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | PostgreSQL 15 (Docker) |
| ETL Pipeline | Apache Airflow 2.7 (Docker) |
| Auth | JWT (python-jose, bcrypt) |
| Testing | pytest, 98% coverage |

---

## Project Structure
```
chamascore/
├── backend/
│   ├── app/
│   │   ├── api/          # REST endpoints
│   │   ├── core/         # Config, security, database
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── scoring/      # Credit scoring engine
│   └── tests/            # 25 unit tests
├── frontend/
│   └── src/
│       ├── pages/        # Login, Register, Dashboard, GroupDetail
│       └── lib/          # Axios API client
├── airflow/
│   └── dags/             # Daily ETL pipeline
├── scripts/
│   └── generate_synthetic_data.py
└── docker-compose.yml
```

---

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 18+
- Docker Desktop

### 1. Clone the repository
```bash
git clone https://github.com/Jlugaho/chamascore.git
cd chamascore
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Start PostgreSQL and Airflow
```bash
docker compose up -d
```

### 4. Start the backend
```bash
cd backend
python -m venv venv
source venv/Scripts/activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 5. Start the frontend
```bash
cd frontend
npm install
npm start
```

### 6. Load sample data (optional)
```bash
cd backend
PYTHONPATH=. python ../scripts/generate_synthetic_data.py
```

---

## Demo Credentials

| Field | Value |
|-------|-------|
| Email | demo@chamascore.co.ke |
| Password | Demo1234 |

---

## API Documentation

Interactive Swagger docs available at: `http://127.0.0.1:8000/api/docs`

Key endpoints:
- `POST /api/v1/auth/register` — Register a new user
- `POST /api/v1/auth/login` — Login and get JWT token
- `GET /api/v1/groups/` — List user's chama groups
- `POST /api/v1/groups/` — Create a new group
- `GET /api/v1/credit-scores/group/{id}` — Get credit score with breakdown
- `POST /api/v1/contributions/` — Record a contribution
- `POST /api/v1/loans/apply` — Apply for a loan

---

## Running Tests
```bash
cd backend
pytest tests/ -v --cov=app/scoring --cov-report=term-missing
```

**Results:** 25 tests, 98% coverage

---

## Airflow ETL Pipeline

The `chamascore_daily_scoring` DAG runs every day at midnight EAT (21:00 UTC):

1. **Extract** — pulls all active groups from PostgreSQL
2. **Calculate** — runs the heuristic scoring engine on each group
3. **Load** — upserts scores back to the database
4. **Summary** — logs a summary of all scores

Access Airflow at: `http://localhost:8080` (admin / admin123)

---

## Services

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://127.0.0.1:8000 |
| API Docs | http://127.0.0.1:8000/api/docs |
| Airflow | http://localhost:8080 |

---

## Author

**Joseph Lugaho**  
GitHub: [@Jlugaho](https://github.com/Jlugaho)