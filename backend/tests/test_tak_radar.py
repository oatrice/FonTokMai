# backend/tests/test_tak_radar.py

import numpy as np
import pytest
from app.services.tmd_radar_config import STATIONS, BoundingBox
from app.services.tmd_radar_catalog import KNOWN_TMD_RADAR_PRESETS
from app.services.tmd_radar.processor import TMDRadarProcessor
from app.services.tmd_radar.clustering import TMDClusteringMixin

def test_tak_station_registered():
    """Verify that 'tak' station is registered correctly in STATIONS dictionary and catalog presets."""
    assert "tak" in STATIONS, "Station 'tak' missing from STATIONS dictionary"
    st = STATIONS["tak"]
    assert st.code == "tak"
    assert st.name == "Doi Muser, Tak Province (240km) / ตาก (ดอยมูเซอ)"
    assert st.static_image_url == "https://weather.tmd.go.th/tak/tak240_latest.jpg"
    assert st.loop_page_url == "https://weather.tmd.go.th/takloop.php"
    assert st.loop_gif_url == "https://weather.tmd.go.th/tak/takloop.gif"
    assert st.center_lat == 16.4856
    assert st.center_lng == 99.1684
    assert st.radius_km == 240.0
    assert isinstance(st.bbox, BoundingBox)

    tak_preset = next((p for p in KNOWN_TMD_RADAR_PRESETS if p["code"] == "tak"), None)
    assert tak_preset is not None, "Tak ('tak') preset missing from KNOWN_TMD_RADAR_PRESETS"
    assert tak_preset["center_lat"] == 16.4856
    assert tak_preset["center_lng"] == 99.1684
    assert tak_preset["radius_km"] == 240.0


def test_tak_pin_pixel_location():
    """Verify that location (17.2743, 99.3106) correctly resolves to pixel (459, 259) in full frame scale."""
    processor = TMDRadarProcessor(station_code="tak")
    px, py = processor.latlng_to_pixel(17.2743, 99.3106, is_loop=False)
    assert abs(px - 459) <= 1, f"Expected x ~459, got {px}"
    assert abs(py - 259) <= 1, f"Expected y ~259, got {py}"


def test_tak_terrain_green_not_detected_as_rain():
    """Verify that background/sea/ground colors in Tak scans are ignored."""
    processor = TMDRadarProcessor(station_code="tak")

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


def test_tak_legitimate_rain_detected():
    """Verify that legitimate rain green and yellow colors are accurately detected for Tak."""
    processor = TMDRadarProcessor(station_code="tak")

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
