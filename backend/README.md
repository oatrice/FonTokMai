# FonMaYang Backend 🌧️⚡

Python FastAPI Backend Service for the FonMaYang Real-Time Rain Prediction & Gamified Financial Transparency System.

## Stack & Architecture
- **Framework:** FastAPI / Python 3.11+
- **Database:** Async SQLAlchemy + SQLite (Dev) / Neon Postgres (Production) / Cloud Firestore
- **Task Queue & Async Jobs:** Cloud Tasks & Cloud Scheduler
- **Broadcasting:** Server-Sent Events (SSE) `/api/v1/events/stream`

## Development Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Running Tests

```bash
pytest tests/ -v
```
