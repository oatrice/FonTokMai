import pytest
from httpx import AsyncClient, ASGITransport
import datetime
from fastapi import FastAPI
from app.routers.financial import router as financial_router
from app.database import Base, engine, AsyncSessionLocal
from app.models import Donor
import pytest_asyncio

app = FastAPI()
app.include_router(financial_router)

@pytest_asyncio.fixture(autouse=True, scope="module")
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_get_leaderboard_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/financial/leaderboard")
        assert response.status_code == 200
        assert response.json() == []

@pytest.mark.asyncio
async def test_get_leaderboard_with_donations():
    async with AsyncSessionLocal() as db:
        # Clear existing
        donors = [
            Donor(token="user1", pseudonym="Alice", hashed_transaction_id="tx1", amount=500.0, timestamp=datetime.datetime.now(datetime.timezone.utc)),
            Donor(token="user1", pseudonym="Alice", hashed_transaction_id="tx2", amount=600.0, timestamp=datetime.datetime.now(datetime.timezone.utc)),
            Donor(token="user2", pseudonym="Bob", hashed_transaction_id="tx3", amount=50.0, timestamp=datetime.datetime.now(datetime.timezone.utc)),
            Donor(token="user3", pseudonym="Charlie", hashed_transaction_id="tx4", amount=1500.0, timestamp=datetime.datetime.now(datetime.timezone.utc)),
        ]
        db.add_all(donors)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/financial/leaderboard")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 3
        # Descending by amount
        assert data[0]["token"] == "user3"
        assert data[0]["total_amount"] == 1500.0
        assert data[0]["pseudonym"] == "Charlie"
        assert data[0]["badge"] == "Ecosystem Guardian"

        assert data[1]["token"] == "user1"
        assert data[1]["total_amount"] == 1100.0
        assert data[1]["pseudonym"] == "Alice"
        assert data[1]["badge"] == "Ecosystem Guardian"

        assert data[2]["token"] == "user2"
        assert data[2]["total_amount"] == 50.0
        assert data[2]["pseudonym"] == "Bob"
        assert data[2]["badge"] == "Supporter"
