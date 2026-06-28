import pytest
import numpy as np
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.tmd_radar_config import STATIONS, DBZ_COLOR_MAPPING, StationConfig, BoundingBox
from app.services.tmd_radar_processor import TMDRadarProcessor

@pytest.mark.asyncio
async def test_latlng_to_pixel_with_calibration():
    # Setup mock station with calibration points and projection
    test_bbox = BoundingBox(lat_max=20.0, lng_min=100.0, lat_min=10.0, lng_max=110.0)
    # Define exact points
    # Let's say top-left (20.0, 100.0) should map to (10, 10) instead of (0, 0)
    # Bottom-right (10.0, 110.0) should map to (90, 90) instead of (100, 100)
    test_config = StationConfig(
        code="test_calib",
        name="Test Calibration",
        static_image_url="http://test",
        loop_page_url="http://test",
        bbox=test_bbox,
        static_crop_x=0, static_crop_y=0, static_crop_width=100, static_crop_height=100,
        loop_crop_x=0, loop_crop_y=0, loop_crop_width=100, loop_crop_height=100,
        projection_type="equirectangular",
        calibration_points={
            (20.0, 100.0): (10.0, 10.0),
            (10.0, 110.0): (90.0, 90.0)
        }
    )
    STATIONS["test_calib"] = test_config
    processor = TMDRadarProcessor(station_code="test_calib")

    # Calculate
    px_x, px_y = processor.latlng_to_pixel(20.0, 100.0)
    assert px_x == 0
    assert px_y == 0

    px_x2, px_y2 = processor.latlng_to_pixel(10.0, 110.0)
    assert px_x2 == 100
    assert px_y2 == 100

@pytest.mark.asyncio
async def test_fetch_loop_gif_and_extract_frames():
    processor = TMDRadarProcessor(station_code="kkn240")
    
    # Mock httpx and imageio
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_response = AsyncMock()
        mock_response.content = b"fake_gif_bytes"
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        with patch('PIL.Image.open') as mock_open, patch('PIL.ImageSequence.Iterator') as mock_iterator:
            mock_img = MagicMock()
            mock_open.return_value = mock_img
            
            mock_frame = MagicMock()
            mock_frame.copy.return_value.convert.return_value = MagicMock()
            
            with patch('numpy.array') as mock_np_array:
                mock_np_array.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
                mock_iterator.return_value = [mock_frame] * 6
                
                frames, dt, loop_bytes = await processor.fetch_loop_gif_and_extract_frames()
                
                assert len(frames) == 6
                assert frames[0].shape == (100, 100, 3)
                assert loop_bytes == b"fake_gif_bytes"
                mock_open.assert_called_once()
                mock_iterator.assert_called_once_with(mock_img)

@pytest.mark.asyncio
async def test_latlng_to_pixel():
    processor = TMDRadarProcessor(station_code="kkn120")
    config = STATIONS["kkn120"]
    
    # Test Center Point
    center_lat = (config.bbox.lat_max + config.bbox.lat_min) / 2
    center_lng = (config.bbox.lng_max + config.bbox.lng_min) / 2
    
    px_x, px_y = processor.latlng_to_pixel(center_lat, center_lng)
    
    # It should be exactly at the center of the crop
    expected_x = config.loop_crop_x + (config.loop_crop_width // 2)
    expected_y = config.loop_crop_y + (config.loop_crop_height // 2)
    
    assert abs(px_x - expected_x) <= 2
    assert abs(px_y - expected_y) <= 2

    # Test Top Left
    tl_x, tl_y = processor.latlng_to_pixel(config.bbox.lat_max, config.bbox.lng_min)
    assert abs(tl_x - config.loop_crop_x) <= 15
    assert abs(tl_y - config.loop_crop_y) <= 15
    
    # Test Out of Bounds
    out_x, out_y = processor.latlng_to_pixel(10.0, 100.0) # Somewhere far
    assert out_x is None
    assert out_y is None

@pytest.mark.asyncio
async def test_extract_dbz_from_image():
    processor = TMDRadarProcessor(station_code="kkn120")
    
    # Frames from PIL are in RGB format (not BGR).
    # DBZ_COLOR_MAPPING keys are also RGB tuples.
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # 50 dBZ = Red in RGB: (255, 0, 0)
    red_color = (255, 0, 0)  # R, G, B — pure red = 50 dBZ
    img[40:60, 40:60] = red_color
    
    # 20 dBZ = Green in RGB: (0, 255, 0)
    green_color = (0, 255, 0)  # R, G, B — pure green = 20 dBZ
    img[10:30, 10:30] = green_color
    
    # Test coordinate mapping to DBZ
    # For a red pixel
    dbz_red = processor.get_dbz_at_pixel(img, x=50, y=50)
    assert dbz_red == 50.0  # Red maps to 50 dBZ
    
    # For a green pixel
    dbz_green = processor.get_dbz_at_pixel(img, x=20, y=20)
    assert dbz_green == 20.0
    
    # For a black background pixel
    dbz_black = processor.get_dbz_at_pixel(img, x=5, y=5)
    assert dbz_black == 0.0


@pytest.mark.asyncio
async def test_optical_flow_motion_prediction():
    processor = TMDRadarProcessor(station_code="kkn120")
    
    # Frame 1: A block at (20, 20)
    frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
    frame1[20:40, 20:40] = (255, 0, 0)
    
    # Frame 2: The block moved to (30, 30) => moving down and right
    frame2 = np.zeros((100, 100, 3), dtype=np.uint8)
    frame2[30:50, 30:50] = (255, 0, 0)
    
    # Calculate motion at pixel (25, 25) which was the center of the block
    flow = processor.calculate_optical_flow([frame1, frame2])
    
    velocity_x, velocity_y = processor.get_flow_vector_at(flow, x=25, y=25)
    
    # Since it moved from 20 to 30, velocity vector should be positive in x and y
    assert velocity_x > 0
    assert velocity_y > 0

@pytest.mark.asyncio
async def test_save_and_cleanup_polled_frames():
    processor = TMDRadarProcessor(station_code="kkn120")
    
    # Fake image bytes
    fake_img = b"GIF89a..."
    
    with patch('google.cloud.storage.Client') as mock_storage_client:
        mock_client_instance = MagicMock()
        mock_storage_client.return_value = mock_client_instance
        
        mock_bucket = MagicMock()
        mock_client_instance.bucket.return_value = mock_bucket
        
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        
        # Test Save
        filename = await processor.save_polled_frame(fake_img)
        assert filename.startswith("radar/kkn120/kkn120_")
        assert filename.endswith(".gif")
        mock_blob.upload_from_string.assert_called_once_with(fake_img, content_type="image/gif")
        
        # Test Cleanup
        import time
        now = int(time.time())
        # Mock blobs: one old, one new
        mock_blob_old = MagicMock()
        mock_blob_old.name = f"radar/kkn120/kkn120_{now - 4 * 3600}.gif"
        
        mock_blob_new = MagicMock()
        mock_blob_new.name = f"radar/kkn120/kkn120_{now - 3600}.gif"
        
        mock_bucket.list_blobs.return_value = [mock_blob_old, mock_blob_new]
        
        deleted_count = await processor.cleanup_old_frames(max_age_hours=3)
        assert deleted_count == 1
        mock_blob_old.delete.assert_called_once()
        mock_blob_new.delete.assert_not_called()

def test_extrapolate_rain_at_pixel():
    processor = TMDRadarProcessor(station_code="kkn120")
    
    # Create a dummy image 100x100
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Put a "rain" pixel at (20, 20) with color (0, 255, 0) -> dBZ > 0
    # Let's say (0, 255, 0) maps to some dBZ.
    # To be safe, we'll mock `get_dbz_at_pixel` to just return 35.0 for (20, 20) and 0.0 elsewhere.
    with patch.object(processor, 'get_dbz_at_pixel', side_effect=lambda i, x, y: 35.0 if x == 20 and y == 20 else 0.0):
        # Create a dummy flow field
        flow = np.zeros((100, 100, 2), dtype=np.float32)
        # Rain is moving right (+dx) and down (+dy) at 5 pixels per step
        flow[:, :, 0] = 5.0
        flow[:, :, 1] = 5.0
        
        # We want to know what happens at target pixel (30, 30) after 2 steps.
        # Rain currently at (20, 20).
        # In 2 steps, rain moves 2 * 5 = +10 in x and y. So it will reach (30, 30).
        # Backward tracking from (30, 30) with 2 steps: src = 30 - 2*5 = 20.
        dbz_future, _, _ = processor.extrapolate_rain_at_pixel(img, flow, px=30, py=30, steps=2)
        assert dbz_future == 35.0
        
        # After 1 step, it should be at (25, 25), so target (30, 30) should have 0 dBZ.
        # We pass radius=0 because the new default radius=5 would still find the pixel at (20, 20).
        dbz_1step, _, _ = processor.extrapolate_rain_at_pixel(img, flow, px=30, py=30, steps=1, radius=0)
        assert dbz_1step == 0.0

def test_draw_pin_on_frame():
    processor = TMDRadarProcessor(station_code="kkn120")
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Original color at center
    assert np.array_equal(img[50, 50], [0, 0, 0])
    
    # Draw pin at (50, 50)
    processor.draw_pin_on_frame(img, 50, 50)
    
    # Check if the pixel at (50, 50) has changed to red (0, 0, 255) in BGR
    assert not np.array_equal(img[50, 50], [0, 0, 0])
    assert img[50, 50][2] > 100  # R channel should be high
    
def test_extrapolate_rain_with_growth_decay():
    processor = TMDRadarProcessor(station_code="kkn120")
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    
    with patch.object(processor, 'get_dbz_at_pixel', side_effect=lambda i, x, y: 40.0 if x == 20 and y == 20 else 0.0):
        flow = np.zeros((100, 100, 2), dtype=np.float32)
        flow[:, :, 0] = 5.0
        flow[:, :, 1] = 5.0
        
        # Test Normal Extrapolation (no growth/decay passed)
        dbz_base, _, _ = processor.extrapolate_rain_at_pixel(img, flow, px=30, py=30, steps=2)
        assert dbz_base == 40.0
        
        # Test with Growth (rate = 0.1 per step) -> 40 * (1 + 0.1)^2 = 48.4
        dbz_growth, _, _ = processor.extrapolate_rain_at_pixel(img, flow, px=30, py=30, steps=2, rate=0.1)
        assert abs(dbz_growth - 48.4) < 0.1
        
        # Test with Decay (rate = -0.1 per step) -> 40 * (1 - 0.1)^2 = 32.4
        dbz_decay, _, _ = processor.extrapolate_rain_at_pixel(img, flow, px=30, py=30, steps=2, rate=-0.1)
        assert abs(dbz_decay - 32.4) < 0.1
        
        # Test Damping/Max threshold (e.g. rate = 2.0 -> very high growth)
        # Should be capped at 75.0 (MAX_DBZ)
        dbz_capped, _, _ = processor.extrapolate_rain_at_pixel(img, flow, px=30, py=30, steps=2, rate=2.0)
        assert dbz_capped == 75.0
        
        # Test Min threshold (e.g. rate = -0.9 -> very high decay)
        # 40 * (0.1)^2 = 0.4 -> below MIN_DBZ (e.g., 10), so should be 0.0
        dbz_min, _, _ = processor.extrapolate_rain_at_pixel(img, flow, px=30, py=30, steps=2, rate=-0.9)
        assert dbz_min == 0.0


def test_parse_html_timestamp_bangkok_to_utc():
    html = '<img src="kkn240_latest.gif?v=250626_1030">'
    dt = TMDRadarProcessor.parse_html_timestamp(html)
    assert dt is not None
    from datetime import timezone
    from zoneinfo import ZoneInfo
    assert dt.astimezone(ZoneInfo("Asia/Bangkok")).strftime("%H:%M") == "10:30"


def test_parse_html_timestamp_missing_returns_none():
    assert TMDRadarProcessor.parse_html_timestamp("<html></html>") is None
