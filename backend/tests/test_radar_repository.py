# backend/tests/test_radar_repository.py

import pytest
import pytest_asyncio
from app.models import RadarStationModel, Base
from app.repositories.radar import RadarStationRepository
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

@pytest_asyncio.fixture
async def async_session():
    # Use SQLite in-memory engine for fast repository testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_upsert_and_get_station(async_session):
    repo = RadarStationRepository(async_session)
    
    station_data = {
        "code": "svp240",
        "name": "Bangkok Suvarnabhumi (240km)",
        "static_image_url": "https://weather.tmd.go.th/svp/svp240_latest.jpg",
        "loop_page_url": "https://weather.tmd.go.th/svpLoop.php",
        "loop_gif_url": "https://weather.tmd.go.th/svp/svp240_HQ_Loop.gif",
        "center_lat": 13.6860,
        "center_lng": 100.7486,
        "radius_km": 240.0,
        "lat_max": 15.85,
        "lng_min": 98.59,
        "lat_min": 11.53,
        "lng_max": 102.91,
        "static_crop_x": 267,
        "static_crop_y": 197,
        "static_crop_width": 402,
        "static_crop_height": 402,
        "loop_crop_x": 267,
        "loop_crop_y": 197,
        "loop_crop_width": 402,
        "loop_crop_height": 402,
        "is_active": True
    }
    
    saved_station = await repo.upsert_station(station_data)
    assert saved_station.code == "svp240"
    assert saved_station.center_lat == 13.6860
    
    fetched = await repo.get_station("svp240")
    assert fetched is not None
    assert fetched.name == "Bangkok Suvarnabhumi (240km)"
    assert fetched.static_crop_x == 267

@pytest.mark.asyncio
async def test_get_all_active_stations(async_session):
    repo = RadarStationRepository(async_session)
    
    st1 = {
        "code": "kkn240",
        "name": "Khon Kaen (240km)",
        "static_image_url": "https://weather.tmd.go.th/kkn/kkn240_latest.gif",
        "center_lat": 16.4322,
        "center_lng": 102.8236,
        "lat_max": 18.59, "lng_min": 100.67, "lat_min": 14.27, "lng_max": 104.99,
        "is_active": True
    }
    st2 = {
        "code": "disabled_st",
        "name": "Disabled Station",
        "static_image_url": "https://weather.tmd.go.th/disabled.gif",
        "center_lat": 10.0, "center_lng": 100.0,
        "lat_max": 11.0, "lng_min": 99.0, "lat_min": 9.0, "lng_max": 101.0,
        "is_active": False
    }
    
    await repo.upsert_station(st1)
    await repo.upsert_station(st2)
    
    active_stations = await repo.get_active_stations()
    codes = [s.code for s in active_stations]
    assert "kkn240" in codes
    assert "disabled_st" not in codes
