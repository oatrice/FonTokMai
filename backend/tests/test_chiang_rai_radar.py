# backend/tests/test_chiang_rai_radar.py

import numpy as np
import pytest
from app.services.tmd_radar_config import STATIONS, BoundingBox
from app.services.tmd_radar_catalog import KNOWN_TMD_RADAR_PRESETS
from app.services.tmd_radar.processor import TMDRadarProcessor
from app.services.tmd_radar.clustering import TMDClusteringMixin

def test_chiang_rai_station_registered():
    """Verify that 'cri' station is registered correctly in STATIONS dictionary and catalog presets."""
    assert "cri" in STATIONS, "Station 'cri' missing from STATIONS dictionary"
    st = STATIONS["cri"]
    assert st.code == "cri"
    assert st.name == "Chiang Rai (240km) / เชียงราย"
    assert st.static_image_url == "https://weather.tmd.go.th/cri/cri240_latest.jpg"
    assert st.loop_page_url == "https://weather.tmd.go.th/criloop.php"
    assert st.loop_gif_url == "https://weather.tmd.go.th/cri/criloop.gif"
    assert st.center_lat == 19.9609
    assert st.center_lng == 99.8824
    assert st.radius_km == 240.0
    assert isinstance(st.bbox, BoundingBox)

    cri_preset = next((p for p in KNOWN_TMD_RADAR_PRESETS if p["code"] == "cri"), None)
    assert cri_preset is not None, "Chiang Rai ('cri') preset missing from KNOWN_TMD_RADAR_PRESETS"
    assert cri_preset["center_lat"] == 19.9609
    assert cri_preset["center_lng"] == 99.8824
    assert cri_preset["radius_km"] == 240.0


def test_chiang_rai_pin_pixel_location():
    """Verify center coordinates (19.9609, 99.8824) land accurately near the center of the radar frame."""
    processor = TMDRadarProcessor(station_code="cri")
    config = STATIONS["cri"]
    center_lat = (config.bbox.lat_max + config.bbox.lat_min) / 2
    center_lng = (config.bbox.lng_max + config.bbox.lng_min) / 2
    px, py = processor.latlng_to_pixel(center_lat, center_lng, is_loop=False)
    expected_x = config.static_crop_x + (config.static_crop_width // 2)
    expected_y = config.static_crop_y + (config.static_crop_height // 2)
    assert abs(px - expected_x) <= 2, f"Expected x {expected_x}, got {px}"
    assert abs(py - expected_y) <= 2, f"Expected y {expected_y}, got {py}"


def test_chiang_rai_terrain_green_not_detected_as_rain():
    """Verify that background/terrain green colors in Chiang Rai scans are ignored as 0 dBZ."""
    processor = TMDRadarProcessor(station_code="cri")

    terrain_colors = [
        (86, 138, 74),
        (86, 139, 75),
        (90, 118, 71),
        (92, 130, 72),
        (85, 140, 72),
        (80, 135, 70),
        (106, 159, 113),
        (94, 163, 108),
        (100, 156, 109),
    ]

    img = np.zeros((10, 10, 3), dtype=np.uint8)

    for color in terrain_colors:
        img[5, 5] = color
        dbz = processor.get_dbz_at_pixel(img, x=5, y=5)
        assert dbz == 0.0, f"Terrain green color {color} was wrongly detected as {dbz} dBZ in scalar get_dbz_at_pixel"

    mixin = TMDClusteringMixin()
    for color in terrain_colors:
        test_frame = np.full((20, 20, 3), color, dtype=np.uint8)
        raw_map = mixin._extract_raw_dbz_map(test_frame)
        mask = mixin.extract_rain_mask(test_frame)
        assert np.max(raw_map) == 0.0, f"Vectorized _extract_raw_dbz_map failed for terrain color {color}"
        assert np.max(mask) == 0, f"Vectorized extract_rain_mask failed for terrain color {color}"


def test_chiang_rai_legitimate_rain_detected():
    """Verify that legitimate rain green and yellow colors are accurately detected for Chiang Rai."""
    processor = TMDRadarProcessor(station_code="cri")

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
