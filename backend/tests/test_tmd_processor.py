import pytest
import numpy as np
from app.services.tmd_radar_config import STATIONS, DBZ_COLOR_MAPPING
from app.services.tmd_radar_processor import TMDRadarProcessor

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
