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
        crop_x=0, crop_y=0, crop_width=100, crop_height=100,
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
    assert px_x == 10
    assert px_y == 10

    px_x2, px_y2 = processor.latlng_to_pixel(10.0, 110.0)
    assert px_x2 == 90
    assert px_y2 == 90

@pytest.mark.asyncio
async def test_fetch_loop_gif_and_extract_frames():
    processor = TMDRadarProcessor(station_code="kkn120")
    
    # Mock httpx and imageio
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_response = AsyncMock()
        mock_response.content = b"fake_gif_bytes"
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        with patch('imageio.v3.imread') as mock_imread:
            # Mock 6 frames of 100x100 RGB
            fake_frames = np.zeros((6, 100, 100, 3), dtype=np.uint8)
            mock_imread.return_value = fake_frames
            
            frames = await processor.fetch_loop_gif_and_extract_frames()
            
            assert len(frames) == 6
            assert frames[0].shape == (100, 100, 3)
            mock_imread.assert_called_once_with(b"fake_gif_bytes", index=None)

@pytest.mark.asyncio
async def test_latlng_to_pixel():
    processor = TMDRadarProcessor(station_code="kkn120")
    config = STATIONS["kkn120"]
    
    # Test Center Point
    center_lat = (config.bbox.lat_max + config.bbox.lat_min) / 2
    center_lng = (config.bbox.lng_max + config.bbox.lng_min) / 2
    
    px_x, px_y = processor.latlng_to_pixel(center_lat, center_lng)
    
    # It should be exactly at the center of the crop
    expected_x = config.crop_x + (config.crop_width // 2)
    expected_y = config.crop_y + (config.crop_height // 2)
    
    assert px_x == expected_x
    assert px_y == expected_y

    # Test Top Left
    tl_x, tl_y = processor.latlng_to_pixel(config.bbox.lat_max, config.bbox.lng_min)
    assert tl_x == config.crop_x
    assert tl_y == config.crop_y
    
    # Test Out of Bounds
    out_x, out_y = processor.latlng_to_pixel(10.0, 100.0) # Somewhere far
    assert out_x is None
    assert out_y is None

@pytest.mark.asyncio
async def test_extract_dbz_from_image():
    processor = TMDRadarProcessor(station_code="kkn120")
    
    # Create a dummy image array (Height, Width, Channels) - BGR for OpenCV
    # Let's make it a 100x100 RGB image filled with black
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Draw a 50 dBZ red box in the middle (BGR format in OpenCV)
    red_color = (0, 0, 255) # B,G,R for Red
    # OpenCV uses BGR by default when reading, and processor unpacks as b,g,r
    img[40:60, 40:60] = red_color
    
    # Draw a 20 dBZ green box
    green_color = (0, 255, 0) # B,G,R for Green
    img[10:30, 10:30] = green_color
    
    # Test coordinate mapping to DBZ
    # For a red pixel
    dbz_red = processor.get_dbz_at_pixel(img, x=50, y=50)
    assert dbz_red == 50.0 # Red maps to 50 dBZ
    
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
