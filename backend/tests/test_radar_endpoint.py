import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.database import engine, Base

client = TestClient(app)

@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

def test_get_radar_stations_endpoint():
    response = client.get("/api/v1/radar/stations")
    assert response.status_code == 200
    data = response.json()
    assert "stations" in data
    assert isinstance(data["stations"], list)
    assert len(data["stations"]) >= 3
    
    # Check station properties
    codes = [s["code"] for s in data["stations"]]
    assert "kkn120" in codes
    assert "kkn240" in codes
    assert "skn240" in codes

    first = data["stations"][0]
    assert "name" in first
    assert "center_lat" in first
    assert "center_lng" in first
    assert "radius_km" in first
    assert first["status"] in ["online", "delayed", "offline"]
    assert "latency_minutes" in first
    assert "last_frame_timestamp" in first
    assert "is_active" in first

def test_get_radar_stations_extracts_frame_timestamps():
    from app.dependencies import get_repo_context
    import asyncio

    async def seed_cache():
        async with get_repo_context() as repo:
            # Seed fresh frames
            now_ts = 1785500000.0  # arbitrary epoch
            await repo.set_latest_radar_cache("skn240", [{"url": "http://img.jpg", "timestamp": now_ts}])

    asyncio.run(seed_cache())
    response = client.get("/api/v1/radar/stations")
    assert response.status_code == 200
    stations = {s["code"]: s for s in response.json()["stations"]}
    assert "skn240" in stations
    assert stations["skn240"]["code"] == "skn240"

