import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from datetime import datetime, timezone
import json
from app.main import app
from app.models import Donor, SystemConfig, Base
from app.database import engine, AsyncSessionLocal

client = TestClient(app)

@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        yield session
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_milestone_normal_state(db_session: AsyncSession):
    # Clear existing
    await db_session.execute(delete(Donor))
    await db_session.execute(delete(SystemConfig).where(SystemConfig.key == "milestone_lock"))
    await db_session.commit()
    
    # Add some donors
    db_session.add(Donor(token="t1", hashed_transaction_id="h1", amount=100.0, timestamp=datetime.now(timezone.utc)))
    db_session.add(Donor(token="t2", hashed_transaction_id="h2", amount=50.0, timestamp=datetime.now(timezone.utc)))
    await db_session.commit()

    response = client.get("/api/milestones")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_amount"] == 150.0
    assert data["is_locked"] == False
    assert data["waiting_list"] == False
    assert len(data["recent_donations"]) == 2
    # Ensure they are anonymized (e.g., no personal info, just amount and fake name or generic)
    assert "token" not in data["recent_donations"][0]

@pytest.mark.asyncio
async def test_milestone_locked_state(db_session: AsyncSession):
    await db_session.execute(delete(SystemConfig).where(SystemConfig.key == "milestone_lock"))
    await db_session.commit()

    db_session.add(SystemConfig(key="milestone_lock", value_json=json.dumps({"locked": True})))
    await db_session.commit()

    response = client.get("/api/milestones")
    assert response.status_code == 200
    data = response.json()
    
    assert data["is_locked"] == True
    assert data["waiting_list"] == True
    assert len(data["recent_donations"]) == 0

