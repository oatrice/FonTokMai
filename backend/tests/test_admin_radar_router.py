# backend/tests/test_admin_radar_router.py

import pytest
import pytest_asyncio
import numpy as np
import cv2
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from app.models import Base
from app.database import AsyncSessionLocal
from app.routers.admin_radar import router as admin_radar_router
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

app = FastAPI()
app.include_router(admin_radar_router, prefix="/api/v1/admin/radar")

from sqlalchemy.pool import StaticPool

@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async def override_get_db():
        async with session_factory() as session:
            yield session

    from app.routers.admin_radar import get_async_db
    app.dependency_overrides[get_async_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()

@pytest.mark.asyncio
async def test_preview_endpoint(client, monkeypatch):
    # Mock HTTP download for radar image
    synthetic_img = np.zeros((800, 800, 3), dtype=np.uint8)
    cv2.circle(synthetic_img, (400, 400), 350, (255, 255, 255), 4)
    _, buffer = cv2.imencode('.jpg', synthetic_img)
    
    class MockResponse:
        status_code = 200
        content = buffer.tobytes()

    def mock_requests_get(*args, **kwargs):
        return MockResponse()

    async def mock_get(*args, **kwargs):
        return MockResponse()

    import httpx
    import requests
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
    monkeypatch.setattr(requests, "get", mock_requests_get)

    payload = {
        "code": "test240",
        "name": "Test Radar (240km)",
        "image_url": "https://weather.tmd.go.th/test/test240_latest.jpg",
        "lat": 13.7,
        "lng": 100.5,
        "radius_km": 240.0
    }
    
    res = await client.post("/api/v1/admin/radar/preview", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "preview_image_base64" in data
    assert data["crop_info"]["static_crop_width"] > 0
    assert "code_snippet" in data

@pytest.mark.asyncio
async def test_save_and_list_stations_endpoints(client):
    station_payload = {
        "code": "cmi240",
        "name": "Chiang Mai (240km)",
        "static_image_url": "https://weather.tmd.go.th/cmi/cmi240_latest.jpg",
        "loop_page_url": "https://weather.tmd.go.th/cmiLoop.php",
        "loop_gif_url": "https://weather.tmd.go.th/cmi/cmiloop.gif",
        "center_lat": 18.77,
        "center_lng": 98.97,
        "radius_km": 240.0,
        "lat_max": 20.93, "lng_min": 96.81, "lat_min": 16.61, "lng_max": 101.13,
        "static_crop_x": 72, "static_crop_y": 28, "static_crop_width": 728, "static_crop_height": 728,
        "loop_crop_x": 72, "loop_crop_y": 28, "loop_crop_width": 728, "loop_crop_height": 728,
        "is_active": True
    }
    
    # Save station
    res = await client.post("/api/v1/admin/radar/stations", json=station_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.json()["code"] == "cmi240"

    # List stations
    res_list = await client.get("/api/v1/admin/radar/stations")
    assert res_list.status_code == 200
    stations = res_list.json()
    assert len(stations) >= 1
    assert stations[0]["code"] == "cmi240"
