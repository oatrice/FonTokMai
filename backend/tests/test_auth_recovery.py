import pytest
from httpx import AsyncClient, ASGITransport
import datetime
from fastapi import FastAPI
from app.routers.auth import router as auth_router
from app.database import Base, engine
import pytest_asyncio

app = FastAPI()
app.include_router(auth_router)

@pytest_asyncio.fixture(autouse=True, scope="module")
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_auth_and_recovery():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Simulate donation success
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        donation_data = {
            "transaction_id": "tx_123456789",
            "amount": 500.0,
            "timestamp": timestamp
        }
        
        response = await ac.post("/auth/generate-token", json=donation_data)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        token = data["token"]
        assert token.startswith("Fon-")
        
        # 2. Recover with correct details
        recovery_data = {
            "transaction_id": "tx_123456789",
            "amount": 500.0,
            "timestamp": timestamp
        }
        rec_resp = await ac.post("/auth/recover", json=recovery_data)
        assert rec_resp.status_code == 200
        rec_data = rec_resp.json()
        assert rec_data["token"] == token
        
        # 3. Recover with wrong transaction ID
        wrong_tx_data = {
            "transaction_id": "tx_999999999",
            "amount": 500.0,
            "timestamp": timestamp
        }
        wrong_tx_resp = await ac.post("/auth/recover", json=wrong_tx_data)
        assert wrong_tx_resp.status_code == 401
        
        # 4. Recover with wrong amount
        wrong_amount_data = {
            "transaction_id": "tx_123456789",
            "amount": 100.0,
            "timestamp": timestamp
        }
        wrong_amount_resp = await ac.post("/auth/recover", json=wrong_amount_data)
        assert wrong_amount_resp.status_code == 401
