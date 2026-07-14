import pytest
import pytest_asyncio
import math
import numpy as np
from unittest.mock import ANY, MagicMock, AsyncMock, patch
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
        # The user-facing lock label must be preserved; the renderer now matches
        # by stored pixel position rather than by the reassigned cluster label.
        assert updated_loc.locked_target_id == "B"

        # Verify the renderer received the stored lock position so it can draw
        # the crosshair at the right cloud independently of cluster label changes.
        mock_processor.generate_radar_tracking_image.assert_called_once()
        renderer_args, _ = mock_processor.generate_radar_tracking_image.call_args
        assert renderer_args[-3] == "B"
        assert renderer_args[-2] == 105
        assert renderer_args[-1] == 105


@pytest.mark.asyncio
async def test_webhook_lock_command_with_location_name(db_session):
    repo = SQLiteLocationRepository(db_session)
    chat_id = 987654
    
    # Save home and work locations
    await repo.save_location(chat_id, 16.4, 102.8, "FOREVER", name="home")
    await repo.save_location(chat_id, 17.8392, 102.5734, "FOREVER", name="work")
    
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
        mock_process.assert_called_with(chat_id, 17.8392, 102.5734, location_name="work")
        mock_wm.load_persistent_cache_to_memory.assert_called_with("kkn240", ANY)

        # 2. Lock D3 without location prefix -> should target LAST_ACTIVE_LOCATION if set
        webhook.LAST_ACTIVE_LOCATION[chat_id] = "work"
        mock_process.reset_mock()
        await webhook.handle_lock_command(chat_id, "/lock D3")
        
        loc_work = await repo.get_location(chat_id, "work")
        assert loc_work.tracking_mode == "manual"
        assert loc_work.locked_target_id == "D3"
        
        mock_process.assert_called_with(chat_id, 17.8392, 102.5734, location_name="work")
        
        # 3. If LAST_ACTIVE_LOCATION is not set, fallback to prioritizing "home"
        webhook.LAST_ACTIVE_LOCATION.pop(chat_id, None)
        # Reset home tracking mode back to auto for testing fallback
        await repo.update_tracking_mode(chat_id=chat_id, tracking_mode="auto", name="home")
        
        mock_process.reset_mock()
        await webhook.handle_lock_command(chat_id, "/lock D4")
        
        loc_home = await repo.get_location(chat_id, "home")
        assert loc_home.tracking_mode == "manual"
        assert loc_home.locked_target_id == "D4"
        
        mock_process.assert_called_with(chat_id, 16.4, 102.8, location_name="home")
        
        # 4. Unlock 'work' specifically
        mock_process.reset_mock()
        await webhook.handle_unlock_command(chat_id, "/unlock work")
        
        loc_work = await repo.get_location(chat_id, "work")
        assert loc_work.tracking_mode == "auto"
        
        loc_home = await repo.get_location(chat_id, "home")
        assert loc_home.tracking_mode == "manual"
        
        mock_process.assert_called_with(chat_id, 17.8392, 102.5734, location_name="work")


@pytest.mark.asyncio
async def test_webhook_grid_lock_scans_rendered_tracking_crop_cell(db_session):
    repo = SQLiteLocationRepository(db_session)
    chat_id = 246810

    await repo.save_location(chat_id, 16.4, 102.8, "FOREVER", name="home")

    mock_repo_context = MagicMock()
    mock_repo_context.__aenter__.return_value = repo

    from app.services.tmd_radar_processor import TMDRadarProcessor

    frame = np.zeros((800, 800, 3), dtype=np.uint8)
    flow = np.zeros((800, 800, 2), dtype=np.float32)
    processor = TMDRadarProcessor("kkn120")
    user_px, user_py = processor.latlng_to_pixel(16.4, 102.8, is_loop=False)
    crop_x1 = max(0, user_px - 120)
    crop_y1 = max(0, user_py - 120)
    crop_x2 = min(frame.shape[1], user_px + 120)
    crop_y2 = min(frame.shape[0], user_py + 120)
    cell_w = (crop_x2 - crop_x1) / 8.0
    cell_h = (crop_y2 - crop_y1) / 8.0
    rain_x = int(crop_x1 + 6 * cell_w + 8)
    rain_y = int(crop_y1 + 4 * cell_h + 8)
    frame[rain_y, rain_x] = (255, 0, 0)
    flow[rain_y, rain_x] = (1.0, 0.0)
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
        assert loc_home.locked_target_cx == rain_x
        assert loc_home.locked_target_cy == rain_y

        success_text = mock_send.await_args.args[1]
        assert "ตั้งค่าล็อคเป้าแมนนวลสำเร็จ" in success_text
        assert "ความแรงฝนสูงสุด: 50.0 dBZ" in success_text


def test_renderer_locks_by_position_not_cluster_label():
    """When the user locks a grid cell like G5, the stored label is a grid label
    (e.g. 'G5') while clusters are relabeled A/B/C each forecast round. The
    renderer must find the locked cloud by its stored pixel position, not by
    matching the grid label to a cluster label.
    """
    import cv2
    import io
    from PIL import Image
    from app.services.tmd_radar_processor import TMDRadarProcessor

    processor = TMDRadarProcessor("kkn120")
    user_x, user_y = 400, 400

    # Green cloud (low dBZ) so the red crosshair stands out in the output.
    cloud_x, cloud_y = 470, 470
    frame = np.full((800, 800, 3), 255, dtype=np.uint8)
    cv2.circle(frame, (cloud_x, cloud_y), 12, (0, 255, 0), -1)

    # Simulate a fresh forecast round where distance-sorting relabeled the cloud
    # as "A", but the user originally locked it as grid cell "G5".
    clouds = [{
        "cx": cloud_x,
        "cy": cloud_y,
        "vx": 1.0,
        "vy": 0.0,
        "dbz_now": 20.0,
        "predicted_dbz": 20.0,
        "dist": 30.0,
        "eta_min": 15.0,
        "approaching": True,
        "label": "A",
        "pixels": [(cloud_x, cloud_y)],
    }]

    img_bytes = processor.generate_radar_tracking_image(
        frame, user_x, user_y, clouds,
        locked_target_id="G5",
        locked_target_cx=cloud_x,
        locked_target_cy=cloud_y,
    )
    assert img_bytes is not None

    img = Image.open(io.BytesIO(img_bytes))
    arr = np.array(img)
    # The crosshair marker is drawn in red by OpenCV. Depending on how PNG
    # channels are loaded, the high-red component may appear in the last
    # channel, so count pixels whose red/final channel is high while the
    # other two channels are low.
    red_pixels = np.sum(
        (arr[:, :, 2] > 200) & (arr[:, :, 0] < 50) & (arr[:, :, 1] < 50)
    )
    assert red_pixels > 0, "Expected a red crosshair/marker to be drawn for the locked cloud"


@pytest.mark.asyncio
async def test_webhook_lock_uses_last_pinned_location(db_session):
    repo = SQLiteLocationRepository(db_session)
    chat_id = 112233
    
    # Save a home location first to make sure it falls back to LAST_PINNED_LOCATION instead of home.
    await repo.save_location(chat_id, 13.75, 100.5, "FOREVER", name="home")
    
    # Set LAST_PINNED_LOCATION
    from app.routers import webhook
    webhook.LAST_PINNED_LOCATION[chat_id] = (15.6, 103.9)
    
    mock_repo_context = MagicMock()
    mock_repo_context.__aenter__.return_value = repo
    
    with patch("app.routers.webhook.get_repo_context", return_value=mock_repo_context), \
         patch("app.routers.webhook.WeatherManager") as MockWMClass, \
         patch("app.routers.webhook.send_telegram_message", new_callable=AsyncMock) as mock_send, \
         patch("app.routers.webhook.process_telegram_location", new_callable=AsyncMock) as mock_process:
         
        mock_wm = MockWMClass.return_value
        
        import numpy as np
        frame = np.zeros((800, 800, 3), dtype=np.uint8)
        flow = np.zeros((800, 800, 2), dtype=np.float32)
        from app.services.tmd_radar_processor import TMDRadarProcessor
        processor = TMDRadarProcessor("kkn120")
        user_px, user_py = processor.latlng_to_pixel(15.6, 103.9, is_loop=False)
        crop_x1 = max(0, user_px - 120)
        crop_y1 = max(0, user_py - 120)
        crop_x2 = min(frame.shape[1], user_px + 120)
        crop_y2 = min(frame.shape[0], user_py + 120)
        cell_w = (crop_x2 - crop_x1) / 8.0
        cell_h = (crop_y2 - crop_y1) / 8.0
        rain_x = int(crop_x1 + 6 * cell_w + 8)
        rain_y = int(crop_y1 + 4 * cell_h + 8)
        frame[rain_y, rain_x] = (255, 0, 0)
        flow[rain_y, rain_x] = (1.0, 0.0)
        cache_data = ([frame], datetime.now(timezone.utc), 0, flow, "static_cache", 15.0, [0])
        mock_wm.load_persistent_cache_to_memory = AsyncMock(return_value=cache_data)
        
        # Execute lock command without location prefix (e.g. "/lock G5")
        await webhook.handle_lock_command(chat_id, "/lock G5")
        
        # Check that it upserted default row to pinned coordinates
        loc_default = await repo.get_location(chat_id, "default")
        assert loc_default is not None
        assert abs(loc_default.latitude - 15.6) < 1e-6
        assert abs(loc_default.longitude - 103.9) < 1e-6
        assert loc_default.tracking_mode == "manual"
        assert loc_default.locked_target_id == "G5"
        
        # Verify it re-forecasts using default row's coords (15.6, 103.9)
        mock_process.assert_called_with(chat_id, 15.6, 103.9, location_name="default")


@pytest.mark.asyncio
async def test_webhook_inline_lock_callback(db_session):
    repo = SQLiteLocationRepository(db_session)
    chat_id = 556677
    
    mock_repo_context = MagicMock()
    mock_repo_context.__aenter__.return_value = repo
    
    from app.routers import webhook
    
    with patch("app.routers.webhook.get_repo_context", return_value=mock_repo_context), \
         patch("app.routers.webhook.WeatherManager") as MockWMClass, \
         patch("app.routers.webhook.process_telegram_location", new_callable=AsyncMock) as mock_process:
         
        mock_wm = MockWMClass.return_value
        mock_wm.predict_rain = AsyncMock(return_value={
            "approaching_clouds": [
                {"cx": 120, "cy": 130, "label": "A"}
            ],
            "all_rain_clusters": []
        })
        
        callback_query = {
            "id": "query_123",
            "from": {"id": chat_id},
            "data": "lock_target_15.0_103.0_A",
            "message": {"message_id": 999}
        }
        
        await webhook.handle_callback_query(callback_query)
        
        loc_default = await repo.get_location(chat_id, "default")
        assert loc_default is not None
        assert abs(loc_default.latitude - 15.0) < 1e-6
        assert abs(loc_default.longitude - 103.0) < 1e-6
        assert loc_default.tracking_mode == "manual"
        assert loc_default.locked_target_id == "A"
        assert loc_default.locked_target_cx == 120
        assert loc_default.locked_target_cy == 130
        
        mock_process.assert_called_with(chat_id, 15.0, 103.0, message_id_to_edit=999, location_name="default")


@pytest.mark.asyncio
async def test_webhook_inline_lock_callback_with_existing_location(db_session):
    repo = SQLiteLocationRepository(db_session)
    chat_id = 556678
    
    await repo.save_location(chat_id, 16.4, 102.8, "FOREVER", name="work")
    
    mock_repo_context = MagicMock()
    mock_repo_context.__aenter__.return_value = repo
    
    from app.routers import webhook
    
    with patch("app.routers.webhook.get_repo_context", return_value=mock_repo_context), \
         patch("app.routers.webhook.WeatherManager") as MockWMClass, \
         patch("app.routers.webhook.process_telegram_location", new_callable=AsyncMock) as mock_process:
         
        mock_wm = MockWMClass.return_value
        mock_wm.predict_rain = AsyncMock(return_value={
            "approaching_clouds": [],
            "all_rain_clusters": [
                {"cx": 200, "cy": 250, "label": "B"}
            ]
        })
        
        callback_query = {
            "id": "query_456",
            "from": {"id": chat_id},
            "data": "lock_target_16.4_102.8_B",
            "message": {"message_id": 999}
        }
        
        await webhook.handle_callback_query(callback_query)
        
        loc_work = await repo.get_location(chat_id, "work")
        assert loc_work is not None
        assert loc_work.tracking_mode == "manual"
        assert loc_work.locked_target_id == "B"
        assert loc_work.locked_target_cx == 200
        assert loc_work.locked_target_cy == 250
        
        loc_default = await repo.get_location(chat_id, "default")
        assert loc_default is None
        
        mock_process.assert_called_with(chat_id, 16.4, 102.8, message_id_to_edit=999, location_name="work")


@pytest.mark.asyncio
async def test_empty_grid_lock_does_not_snap_to_adjacent_cluster(db_session):
    repo = SQLiteLocationRepository(db_session)
    chat_id = "889900"
    
    # Save a default location
    loc = await repo.save_location(chat_id, 16.4, 102.8, "FOREVER", name="default")
    
    from app.services.tmd_radar_processor import TMDRadarProcessor
    processor = TMDRadarProcessor("kkn120")
    user_px, user_py = processor.latlng_to_pixel(16.4, 102.8, is_loop=False)
    
    crop_r = 120
    crop_x1 = max(0, user_px - crop_r)
    crop_y1 = max(0, user_py - crop_r)
    crop_x2 = min(800, user_px + crop_r)
    crop_y2 = min(800, user_py + crop_r)
    cell_w = (crop_x2 - crop_x1) / 8.0
    cell_h = (crop_y2 - crop_y1) / 8.0
    
    # Center of E4 (col_idx=4, row_idx=3)
    e4_cx = int(crop_x1 + 4.5 * cell_w)
    e4_cy = int(crop_y1 + 3.5 * cell_h)
    
    # Lock target to grid E4 with coordinates of E4 center (empty lock)
    await repo.update_tracking_mode(
        chat_id=chat_id,
        tracking_mode="manual",
        locked_target_id="E4",
        locked_target_cx=e4_cx,
        locked_target_cy=e4_cy,
        name="default"
    )
    
    wm = WeatherManager()
    
    import time
    mock_frames = [np.zeros((800, 800, 3), dtype=np.uint8), np.zeros((800, 800, 3), dtype=np.uint8)]
    mock_flow = np.zeros((800, 800, 2), dtype=np.float32)
    wm.load_persistent_cache_to_memory = AsyncMock(return_value=(
        mock_frames, datetime.now(timezone.utc), time.time(), mock_flow,
        "static_cache", 15.0, [int(time.time()) - 900, int(time.time())]
    ))
    
    # A cluster exists in D4 (col_idx=3, row_idx=3)
    d4_cx = int(crop_x1 + 3.5 * cell_w)
    d4_cy = int(crop_y1 + 3.5 * cell_h)
    
    mock_all_clusters = [
        {"cx": d4_cx, "cy": d4_cy, "vx": 1.0, "vy": 1.0, "dbz_now": 30.0, "growth_rate": 0.1, "label": "A", "pixels": [(d4_cx, d4_cy)]}
    ]
    
    mock_repo_context = MagicMock()
    mock_repo_context.__aenter__.return_value = repo
    
    with patch("app.services.weather_manager.get_repo_context", return_value=mock_repo_context), \
         patch("app.services.weather_manager.TMDRadarProcessor") as MockProcessorClass:
         
        mock_processor = MockProcessorClass.return_value
        mock_processor.latlng_to_pixel.return_value = (user_px, user_py)
        mock_processor.get_dbz_at_pixel.return_value = 0.0
        mock_processor.find_approaching_clouds.return_value = []
        mock_processor.get_all_rain_clusters.return_value = mock_all_clusters
        mock_processor.extrapolate_rain_at_pixel.return_value = (0.0, user_px, user_py)
        mock_processor.render_rain_summary.return_value = "Summary"
        mock_processor.generate_radar_tracking_image.return_value = b"bytes"
        
        await wm._get_tmd_prediction(16.4, 102.8, force_station="kkn120", chat_id=chat_id)
        
        updated_loc = await repo.get_location(chat_id, "default")
        assert updated_loc.locked_target_cx == e4_cx
        assert updated_loc.locked_target_cy == e4_cy


@pytest.mark.asyncio
async def test_webhook_lock_command_with_cloud_label(db_session):
    repo = SQLiteLocationRepository(db_session)
    chat_id = 998877
    
    await repo.save_location(chat_id, 16.4, 102.8, "FOREVER", name="home")
    
    mock_repo_context = MagicMock()
    mock_repo_context.__aenter__.return_value = repo
    
    from app.routers import webhook
    
    with patch("app.routers.webhook.get_repo_context", return_value=mock_repo_context), \
         patch("app.services.weather_manager.WeatherManager") as MockWMClass, \
         patch("app.routers.webhook.send_telegram_message", new_callable=AsyncMock) as mock_send, \
         patch("app.routers.webhook.process_telegram_location", new_callable=AsyncMock) as mock_process:
         
        mock_wm = MockWMClass.return_value
        
        import numpy as np
        frame = np.zeros((800, 800, 3), dtype=np.uint8)
        flow = np.zeros((800, 800, 2), dtype=np.float32)
        flow[300, 350] = (2.5, -1.0)
        cache_data = ([frame], datetime.now(timezone.utc), 0, flow, "static_cache", 15.0, [0])
        mock_wm.load_persistent_cache_to_memory = AsyncMock(return_value=cache_data)
        
        mock_wm.predict_rain = AsyncMock(return_value={
            "approaching_clouds": [
                {"cx": 350, "cy": 300, "label": "A", "dbz_now": 35.0}
            ],
            "all_rain_clusters": []
        })
        
        await webhook.handle_lock_command(chat_id, "/lock A")
        
        loc_home = await repo.get_location(chat_id, "home")
        assert loc_home is not None
        assert loc_home.tracking_mode == "manual"
        assert loc_home.locked_target_id == "A"
        assert loc_home.locked_target_cx == 350
        assert loc_home.locked_target_cy == 300
        
        mock_process.assert_called_with(chat_id, 16.4, 102.8, location_name="home")


@pytest.mark.asyncio
async def test_weather_manager_manual_restrict_other_clouds(db_session):
    repo = SQLiteLocationRepository(db_session)
    chat_id = "112233"
    
    # Save a default location
    await repo.save_location(chat_id, 13.75, 100.5, "FOREVER", name="default")
    await repo.update_tracking_mode(
        chat_id=chat_id,
        tracking_mode="manual",
        locked_target_id="A",
        locked_target_cx=100,
        locked_target_cy=100,
        name="default"
    )
    
    # Setup mocks
    mock_processor = MagicMock()
    # Mocking extrapolate_rain_at_pixel returning (dbz, src_x, src_y)
    # Step 0: returns 0.0 dbz
    # Step 1: returns 35.0 dbz, but source pixel is (300, 300) which is far from locked target projected center (103, 104)
    mock_processor.extrapolate_rain_at_pixel.side_effect = [
        (0.0, 150, 150),
        (35.0, 300, 300),  # This is far away from the locked target A
    ]
    mock_processor.get_dbz_at_pixel.return_value = 0.0
    mock_processor.render_rain_summary.return_value = "☀️ ยังไม่มีแนวโน้มฝนตก"
    mock_processor.get_wind_speed_kmh_from_vector.return_value = 15.0
    mock_processor.get_wind_direction_text_from_vector.return_value = "ENE"
    mock_processor.generate_radar_tracking_image.return_value = b"mock_tracking_bytes"
    mock_processor.generate_timeline_image.return_value = b"mock_timeline_bytes"
    mock_processor.generate_multiframe_analysis_image.return_value = b"mock_multiframe_bytes"
    
    with patch("app.services.weather_manager.get_repo_context") as mock_get_repo_ctx, \
         patch("app.services.weather_manager.TMDRadarProcessor", return_value=mock_processor), \
         patch("app.services.weather_manager._DEV_CONFIG", {"verbose": True, "decay_enabled": True, "prediction_steps": 2, "hit_radius": 8}):
        
        mock_repo_context = MagicMock()
        mock_repo_context.__aenter__.return_value = repo
        mock_get_repo_ctx.return_value = mock_repo_context
        
        wm = WeatherManager()
        wm.processor = mock_processor
        
        curr_frame = np.zeros((800, 800, 3), dtype=np.uint8)
        flow = np.zeros((800, 800, 2), dtype=np.float32)
        
        # Locked cloud is A at (100, 100) moving with vx=3, vy=4
        clouds = [
            {
                "cx": 100, "cy": 100,
                "vx": 3.0, "vy": 4.0,
                "growth_rate": 0.0,
                "label": "A"
            }
        ]
        
        # mock load_persistent_cache_to_memory
        import time
        mock_frames = [np.zeros((800, 800, 3), dtype=np.uint8), np.zeros((800, 800, 3), dtype=np.uint8)]
        wm.load_persistent_cache_to_memory = AsyncMock(return_value=(
            mock_frames, datetime.now(timezone.utc), time.time(), flow,
            "static_cache", 15.0, [int(time.time()) - 900, int(time.time())]
        ))
        
        mock_processor.latlng_to_pixel.return_value = (150, 150)
        mock_processor.find_approaching_clouds.return_value = clouds
        mock_processor.get_all_rain_clusters.return_value = clouds
        
        result = await wm._get_tmd_prediction(
            lat=13.75,
            lng=100.5,
            force_station="kkn120",
            chat_id=chat_id,
            location_name="default",
            mock_state=None
        )
        
        # Verify that for step 1, dbz was filtered/reset to 0.0 because (300, 300) is far from the projected position of A (103, 104)
        assert result is not None
        assert len(result["predictions"]) == 2
        # Step 0 (0.0 dbz)
        assert result["predictions"][0]["dbz"] == 0.0
        # Step 1 (should be 0.0 dbz because it was filtered out, even though extrapolate returned 35.0)
        assert result["predictions"][1]["dbz"] == 0.0


def test_render_rain_summary_with_locked_target_id():
    from app.services.tmd_radar_processor import TMDRadarProcessor
    
    predictions = [
        {"time_offset": 15, "dbz": 30.0, "intensity": "ฝนปานกลาง", "rain": 1.5, "cluster": "A"}
    ]
    
    # 1. Grid cell suffix
    summary_grid = TMDRadarProcessor.render_rain_summary(
        predictions=predictions,
        time_offset_min=0.0,
        confidence_score=1.0,
        locked_target_id="E3"
    )
    assert "(ช่องตาราง [E3])" in summary_grid
    
    # 2. Cloud label suffix
    summary_cloud = TMDRadarProcessor.render_rain_summary(
        predictions=predictions,
        time_offset_min=0.0,
        confidence_score=1.0,
        locked_target_id="A"
    )
    assert "(กลุ่มฝน [A])" in summary_cloud
    
    # 3. Coordinate manual suffix
    summary_coord = TMDRadarProcessor.render_rain_summary(
        predictions=predictions,
        time_offset_min=0.0,
        confidence_score=1.0,
        locked_target_id="MANUAL"
    )
    assert "(พิกัดแมนนวล)" in summary_coord

    # 4. No-rain grid cell with no cloud (empty/dissipated)
    predictions_clear = [{"time_offset": 15, "dbz": 0.0, "intensity": "ไม่มีฝน", "rain": 0.0, "cluster": None}]
    summary_clear_grid = TMDRadarProcessor.render_rain_summary(
        predictions=predictions_clear,
        time_offset_min=0.0,
        confidence_score=1.0,
        locked_target_id="E3",
        approaching_clouds=[]
    )
    assert "(เนื่องจากช่องตาราง [E3] ไม่มีกลุ่มฝนในตำแหน่งล็อกหรือสลายตัวไปแล้ว)" in summary_clear_grid

    # 5. No-rain cloud label that is moving away (present in approaching_clouds or all_rain_clusters)
    summary_clear_cloud = TMDRadarProcessor.render_rain_summary(
        predictions=predictions_clear,
        time_offset_min=0.0,
        confidence_score=1.0,
        locked_target_id="A",
        approaching_clouds=[{"label": "A", "eta_min": 9999}],
        all_rain_clusters=[{"label": "A", "eta_min": 9999}],
        v_close_kmh=-5.4,
        v_actual_kmh=22.2
    )
    assert "(เนื่องจากกลุ่มฝน [A] มีแนวโน้มเคลื่อนที่ขนานหรือออกห่างจากตำแหน่งคุณ:\n- ความเร็วเส้นสีน้ำเงิน: 22.2 กม./ชม.\n- ความเร็วเส้นสีน้ำเงินที่โปรเจกต์บนเส้นสีเขียว: -5.4 กม./ชม.)" in summary_clear_cloud







