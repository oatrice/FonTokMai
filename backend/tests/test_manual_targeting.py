import pytest
import pytest_asyncio
import math
import numpy as np
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.models import Base, UserLocation
from app.repositories.sqlite import SQLiteLocationRepository
from app.services.weather_manager import WeatherManager

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestingSessionLocal() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_repository_update_tracking_mode(db_session):
    repo = SQLiteLocationRepository(db_session)
    chat_id = "123456"
    
    # Save a default location first
    await repo.save_location(chat_id, 13.75, 100.5, "FOREVER", name="default")
    
    # Verify default state
    loc = await repo.get_location(chat_id, "default")
    assert loc.tracking_mode == "auto"
    assert loc.locked_target_id is None
    
    # Update to manual mode
    await repo.update_tracking_mode(
        chat_id=chat_id,
        tracking_mode="manual",
        locked_target_id="A",
        locked_target_cx=100,
        locked_target_cy=200,
        name="default"
    )
    
    # Verify manual state
    loc = await repo.get_location(chat_id, "default")
    assert loc.tracking_mode == "manual"
    assert loc.locked_target_id == "A"
    assert loc.locked_target_cx == 100
    assert loc.locked_target_cy == 200
    
    # Update back to auto mode (unlock)
    await repo.update_tracking_mode(
        chat_id=chat_id,
        tracking_mode="auto",
        name="default"
    )
    
    loc = await repo.get_location(chat_id, "default")
    assert loc.tracking_mode == "auto"
    assert loc.locked_target_id is None
    assert loc.locked_target_cx is None

@pytest.mark.asyncio
async def test_weather_manager_manual_targeting_override(db_session):
    # Test that WeatherManager uses the manual locked target for rate/velocity
    # instead of the auto closest one.
    
    # Pre-populate location with manual target tracking
    repo = SQLiteLocationRepository(db_session)
    chat_id = "77777"
    loc = await repo.save_location(chat_id, 13.75, 100.5, "FOREVER", name="default")
    await repo.update_tracking_mode(
        chat_id=chat_id,
        tracking_mode="manual",
        locked_target_id="B",
        locked_target_cx=100,
        locked_target_cy=100,
        name="default"
    )
    
    # Mocking the optical flow / radar processing data in WeatherManager
    wm = WeatherManager()
    
    import time
    import numpy as np
    mock_frames = [np.zeros((800, 800, 3), dtype=np.uint8), np.zeros((800, 800, 3), dtype=np.uint8)]
    mock_flow = np.zeros((800, 800, 2), dtype=np.float32)
    wm.load_persistent_cache_to_memory = AsyncMock(return_value=(
        mock_frames, datetime.now(timezone.utc), time.time(), mock_flow,
        "static_cache", 15.0, [int(time.time()) - 900, int(time.time())]
    ))
    
    # Mock return values of find_approaching_clouds and get_all_rain_clusters
    mock_all_clusters = [
        {"cx": 105, "cy": 105, "vx": 3.0, "vy": 4.0, "dbz_now": 30.0, "growth_rate": 0.1, "label": "B", "pixels": [(105, 105)]},
        {"cx": 50, "cy": 50, "vx": 1.0, "vy": 1.0, "dbz_now": 40.0, "growth_rate": 0.05, "label": "A", "pixels": [(50, 50)]}
    ]
    
    # Target "B" is closer to (100, 100) (dist = ~7), while "A" is closer to user (dist = ~50)
    # Auto-tracking would choose "A", but manual target tracking should choose "B" because of the lock!
    
    # Let's mock a get_repo_context to return our test repo
    mock_repo_context = MagicMock()
    mock_repo_context.__aenter__.return_value = repo
    
    from unittest.mock import ANY
    with patch("app.services.weather_manager.get_repo_context", return_value=mock_repo_context), \
         patch("app.services.weather_manager.TMDRadarProcessor") as MockProcessorClass:
         
        mock_processor = MockProcessorClass.return_value
        mock_processor.latlng_to_pixel.return_value = (150, 150)
        mock_processor.get_dbz_at_pixel.return_value = 0.0
        
        # mock find_approaching_clouds
        mock_processor.find_approaching_clouds.return_value = [
            {"cx": 105, "cy": 105, "vx": 3.0, "vy": 4.0, "dbz_now": 30.0, "growth_rate": 0.1, "label": "B", "approaching": True},
            {"cx": 50, "cy": 50, "vx": 1.0, "vy": 1.0, "dbz_now": 40.0, "growth_rate": 0.05, "label": "A", "approaching": True}
        ]
        
        mock_processor.get_all_rain_clusters.return_value = mock_all_clusters
        mock_processor.extrapolate_rain_at_pixel.return_value = (15.0, 105, 105)
        mock_processor.render_rain_summary.return_value = "Summary"
        mock_processor.generate_radar_tracking_image.return_value = b"bytes"
        
        # Run tmd prediction
        result = await wm._get_tmd_prediction(13.75, 100.5, force_station="kkn120", chat_id=chat_id)
        
        # Verify extrapolate_rain_at_pixel was called with locked target's vx, vy, and growth_rate
        # growth_rate is passed as rate, fallback_vx/vy as fallback_vx/vy
        mock_processor.extrapolate_rain_at_pixel.assert_any_call(
            ANY, ANY, 150, 150, steps=1, rate=0.1, radius=ANY,
            fallback_vx=3.0, fallback_vy=4.0
        )
        
        # Verify the database was updated with the new coordinates of target B
        updated_loc = await repo.get_location(chat_id, "default")
        assert updated_loc.locked_target_cx == 105
        assert updated_loc.locked_target_cy == 105
        # The label was updated to "A" (since the matched cluster at index 0 gets label "A")
        assert updated_loc.locked_target_id == "A"


@pytest.mark.asyncio
async def test_webhook_lock_command_with_location_name(db_session):
    repo = SQLiteLocationRepository(db_session)
    chat_id = 987654
    
    # Save home and work locations
    await repo.save_location(chat_id, 13.0, 100.0, "FOREVER", name="home")
    await repo.save_location(chat_id, 14.0, 101.0, "FOREVER", name="work")
    
    # Mock repo context in webhook
    mock_repo_context = MagicMock()
    mock_repo_context.__aenter__.return_value = repo
    
    from app.routers import webhook
    
    with patch("app.routers.webhook.get_repo_context", return_value=mock_repo_context), \
         patch("app.services.weather_manager.WeatherManager") as MockWMClass, \
         patch("app.routers.webhook.send_telegram_message", new_callable=AsyncMock) as mock_send, \
         patch("app.routers.webhook.process_telegram_location", new_callable=AsyncMock) as mock_process:
         
        mock_wm = MockWMClass.return_value
        mock_wm.load_persistent_cache_to_memory = AsyncMock(return_value=None)
         
        # 1. Lock 'work' to D2
        await webhook.handle_lock_command(chat_id, "/lock work D2")
        
        # Verify only 'work' is updated to manual
        loc_work = await repo.get_location(chat_id, "work")
        assert loc_work.tracking_mode == "manual"
        assert loc_work.locked_target_id == "D2"
        
        loc_home = await repo.get_location(chat_id, "home")
        assert loc_home.tracking_mode == "auto"
        
        # Verify process_telegram_location was called with work's coordinates
        mock_process.assert_called_with(chat_id, 14.0, 101.0, location_name="work")

        # 2. Lock D3 without location prefix -> should target LAST_ACTIVE_LOCATION if set
        webhook.LAST_ACTIVE_LOCATION[chat_id] = "work"
        mock_process.reset_mock()
        await webhook.handle_lock_command(chat_id, "/lock D3")
        
        loc_work = await repo.get_location(chat_id, "work")
        assert loc_work.tracking_mode == "manual"
        assert loc_work.locked_target_id == "D3"
        
        mock_process.assert_called_with(chat_id, 14.0, 101.0, location_name="work")
        
        # 3. If LAST_ACTIVE_LOCATION is not set, fallback to prioritizing "home"
        webhook.LAST_ACTIVE_LOCATION.pop(chat_id, None)
        # Reset home tracking mode back to auto for testing fallback
        await repo.update_tracking_mode(chat_id=chat_id, tracking_mode="auto", name="home")
        
        mock_process.reset_mock()
        await webhook.handle_lock_command(chat_id, "/lock D4")
        
        loc_home = await repo.get_location(chat_id, "home")
        assert loc_home.tracking_mode == "manual"
        assert loc_home.locked_target_id == "D4"
        
        mock_process.assert_called_with(chat_id, 13.0, 100.0, location_name="home")
        
        # 4. Unlock 'work' specifically
        mock_process.reset_mock()
        await webhook.handle_unlock_command(chat_id, "/unlock work")
        
        loc_work = await repo.get_location(chat_id, "work")
        assert loc_work.tracking_mode == "auto"
        
        loc_home = await repo.get_location(chat_id, "home")
        assert loc_home.tracking_mode == "manual"
        
        mock_process.assert_called_with(chat_id, 14.0, 101.0, location_name="work")


@pytest.mark.asyncio
async def test_webhook_grid_lock_scans_rendered_grid_cell_size(db_session):
    repo = SQLiteLocationRepository(db_session)
    chat_id = 246810

    await repo.save_location(chat_id, 16.4, 102.8, "FOREVER", name="home")

    mock_repo_context = MagicMock()
    mock_repo_context.__aenter__.return_value = repo

    frame = np.zeros((720, 720, 3), dtype=np.uint8)
    # G5 on the rendered 8x8 overlay is x=540..629, y=360..449 for a 720px image.
    # This red rain pixel is inside rendered G5, but outside the old hardcoded
    # 800px G5 area of x=600..699, y=400..499.
    frame[370, 550] = (255, 0, 0)
    flow = np.zeros((720, 720, 2), dtype=np.float32)
    flow[370, 550] = (1.0, 0.0)
    cache_data = ([frame], datetime.now(timezone.utc), 0, flow, "static_cache", 15.0, [0])

    from app.routers import webhook

    with patch("app.routers.webhook.get_repo_context", return_value=mock_repo_context), \
         patch("app.services.weather_manager.WeatherManager") as MockWMClass, \
         patch("app.routers.webhook.send_telegram_message", new_callable=AsyncMock) as mock_send, \
         patch("app.routers.webhook.process_telegram_location", new_callable=AsyncMock):

        mock_wm = MockWMClass.return_value
        mock_wm.load_persistent_cache_to_memory = AsyncMock(return_value=cache_data)

        await webhook.handle_lock_command(chat_id, "/lock home G5")

        loc_home = await repo.get_location(chat_id, "home")
        assert loc_home.tracking_mode == "manual"
        assert loc_home.locked_target_id == "G5"
        assert loc_home.locked_target_cx == 585
        assert loc_home.locked_target_cy == 405

        success_text = mock_send.await_args.args[1]
        assert "ตั้งค่าล็อคเป้าแมนนวลสำเร็จ" in success_text
        assert "ความแรงฝนสูงสุด: 50.0 dBZ" in success_text
