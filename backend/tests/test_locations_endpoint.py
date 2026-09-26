import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import engine, Base, AsyncSessionLocal
from app.models import UserLocation

@pytest.mark.asyncio
async def test_get_locations_endpoint_auth(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "test_secret_key_123")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        loc = UserLocation(
            chat_id="test_chat_1",
            name="Office Test",
            latitude=13.7563,
            longitude=100.5018,
            retention_type="FOREVER",
            presence_policy="always_ask",
            presence_answer_ttl_minutes=120,
            is_snoozed=False
        )
        session.add(loc)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Unauthenticated request should be rejected with 401
        res_unauth = await ac.get("/api/locations")
        assert res_unauth.status_code == 401
        assert res_unauth.json()["detail"] == "Unauthorized"

        # 2. Invalid secret should be rejected with 401
        res_invalid = await ac.get("/api/locations", headers={"x-cron-secret": "wrong_key"})
        assert res_invalid.status_code == 401

        # 3. Authenticated request with correct header succeeds
        response = await ac.get("/api/locations", headers={"x-cron-secret": "test_secret_key_123"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        item = data[0]
        assert item["chat_id"] == "test_chat_1"
        assert item["platform"] == "telegram"
        assert item["name"] == "Office Test"
        assert item["latitude"] == 13.7563
        assert item["longitude"] == 100.5018
        assert item["presence_policy"] == "always_ask"
        assert item["presence_answer_ttl_minutes"] == 120
        assert item["is_snoozed"] is False

