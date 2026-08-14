# backend/tests/test_hat_yai_radar.py

import numpy as np
import pytest
from app.services.tmd_radar_config import STATIONS, BoundingBox
from app.services.tmd_radar_catalog import KNOWN_TMD_RADAR_PRESETS
from app.services.tmd_radar.processor import TMDRadarProcessor
from app.services.tmd_radar.clustering import TMDClusteringMixin

def test_hat_yai_station_registered():
    """Verify that 'hyi' station is registered correctly in STATIONS dictionary and catalog presets."""
    assert "hyi" in STATIONS, "Station 'hyi' missing from STATIONS dictionary"
    st = STATIONS["hyi"]
    assert st.code == "hyi"
    assert st.name == "Hat Yai (240km) / หาดใหญ่"
    assert st.static_image_url == "https://weather.tmd.go.th/hyi/hyi240_latest.jpg"
    assert st.loop_page_url == "https://weather.tmd.go.th/hyiloop.php"
    assert st.loop_gif_url == "https://weather.tmd.go.th/hyi/hyiloop.gif"
    assert st.center_lat == 6.9248
    assert st.center_lng == 100.4385
    assert st.radius_km == 240.0
    assert isinstance(st.bbox, BoundingBox)

    hyi_preset = next((p for p in KNOWN_TMD_RADAR_PRESETS if p["code"] == "hyi"), None)
    assert hyi_preset is not None, "Hat Yai ('hyi') preset missing from KNOWN_TMD_RADAR_PRESETS"
    assert hyi_preset["center_lat"] == 6.9248
    assert hyi_preset["center_lng"] == 100.4385
    assert hyi_preset["radius_km"] == 240.0


def test_hat_yai_pin_pixel_location():
    """Verify center coordinates (6.9248, 100.4385) land accurately in cropped frame space."""
    processor = TMDRadarProcessor(station_code="hyi")
    config = STATIONS["hyi"]

    # In full uncropped canvas (800x800)
    full_px, full_py = processor.latlng_to_pixel(config.center_lat, config.center_lng, is_loop=True)
    expected_full_x = config.loop_crop_x + (config.loop_crop_width // 2)
    expected_full_y = config.loop_crop_y + (config.loop_crop_height // 2)
    assert abs(full_px - expected_full_x) <= 2, f"Expected full x {expected_full_x}, got {full_px}"
    assert abs(full_py - expected_full_y) <= 2, f"Expected full y {expected_full_y}, got {full_py}"

    # In cropped frame space (720x720)
    crop_px, crop_py = processor.latlng_to_pixel(config.center_lat, config.center_lng, is_loop=True, frame_shape=(720, 720))
    assert crop_px == 360, f"Expected cropped center_x 360, got {crop_px}"
    assert crop_py == 360, f"Expected cropped center_y 360, got {crop_py}"


def test_hat_yai_maritime_and_terrain_colors_not_detected_as_rain():
    """Verify that sea background / terrain colors in Hat Yai scans are ignored as 0 dBZ."""
    processor = TMDRadarProcessor(station_code="hyi")

    background_colors = [
        (86, 138, 74),   # Terrain green
        (90, 118, 71),   # Terrain olive
        (106, 159, 113), # Light terrain green
        (15, 35, 75),    # Deep ocean blue
        (20, 50, 100),   # Maritime blue background
    ]

    img = np.zeros((10, 10, 3), dtype=np.uint8)

    for color in background_colors:
        img[5, 5] = color
        dbz = processor.get_dbz_at_pixel(img, x=5, y=5)
        assert dbz == 0.0, f"Background color {color} was wrongly detected as {dbz} dBZ in scalar get_dbz_at_pixel"

    mixin = TMDClusteringMixin()
    for color in background_colors:
        test_frame = np.full((20, 20, 3), color, dtype=np.uint8)
        raw_map = mixin._extract_raw_dbz_map(test_frame)
        mask = mixin.extract_rain_mask(test_frame)
        assert np.max(raw_map) == 0.0, f"Vectorized _extract_raw_dbz_map failed for background color {color}"
        assert np.max(mask) == 0, f"Vectorized extract_rain_mask failed for background color {color}"


def test_hat_yai_legitimate_rain_detected():
    """Verify that legitimate rain green and yellow colors are accurately detected for Hat Yai."""
    processor = TMDRadarProcessor(station_code="hyi")

    rain_colors = [
        (0, 255, 0),    # Bright green
        (4, 248, 3),    # Radar green
        (255, 255, 0),  # Yellow
        (255, 128, 0),  # Orange
    ]

    img = np.zeros((10, 10, 3), dtype=np.uint8)

    for color in rain_colors:
        img[5, 5] = color
        dbz = processor.get_dbz_at_pixel(img, x=5, y=5)
        assert dbz >= 20.0, f"Rain color {color} was wrongly ignored as {dbz} dBZ"
