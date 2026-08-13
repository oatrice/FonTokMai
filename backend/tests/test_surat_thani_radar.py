# backend/tests/test_surat_thani_radar.py

import numpy as np
import pytest
from app.services.tmd_radar_config import STATIONS, BoundingBox
from app.services.tmd_radar_catalog import KNOWN_TMD_RADAR_PRESETS
from app.services.tmd_radar.processor import TMDRadarProcessor
from app.services.tmd_radar.clustering import TMDClusteringMixin

def test_surat_thani_station_registered():
    """Verify that 'srt' station is registered correctly in STATIONS dictionary and catalog presets."""
    assert "srt" in STATIONS, "Station 'srt' missing from STATIONS dictionary"
    st = STATIONS["srt"]
    assert st.code == "srt"
    assert st.name == "Surat Thani (240km) / สุราษฎร์ธานี"
    assert st.static_image_url == "https://weather.tmd.go.th/srt/srt240_latest.jpg"
    assert st.loop_page_url == "https://weather.tmd.go.th/srtloop.php"
    assert st.loop_gif_url == "https://weather.tmd.go.th/srt/srtloop.gif"
    assert st.center_lat == 9.1333
    assert st.center_lng == 99.3333
    assert st.radius_km == 240.0
    assert isinstance(st.bbox, BoundingBox)

    srt_preset = next((p for p in KNOWN_TMD_RADAR_PRESETS if p["code"] == "srt"), None)
    assert srt_preset is not None, "Surat Thani ('srt') preset missing from KNOWN_TMD_RADAR_PRESETS"
    assert srt_preset["center_lat"] == 9.1333
    assert srt_preset["center_lng"] == 99.3333
    assert srt_preset["radius_km"] == 240.0


def test_surat_thani_pin_pixel_location():
    """Verify center coordinates (9.1333, 99.3333) land accurately near the center of the radar frame."""
    processor = TMDRadarProcessor(station_code="srt")
    config = STATIONS["srt"]
    center_lat = (config.bbox.lat_max + config.bbox.lat_min) / 2
    center_lng = (config.bbox.lng_max + config.bbox.lng_min) / 2
    px, py = processor.latlng_to_pixel(center_lat, center_lng, is_loop=False)
    expected_x = config.static_crop_x + (config.static_crop_width // 2)
    expected_y = config.static_crop_y + (config.static_crop_height // 2)
    assert abs(px - expected_x) <= 2, f"Expected x {expected_x}, got {px}"
    assert abs(py - expected_y) <= 2, f"Expected y {expected_y}, got {py}"


def test_surat_thani_maritime_and_terrain_colors_not_detected_as_rain():
    """Verify that sea background / terrain colors in Surat Thani scans are ignored as 0 dBZ."""
    processor = TMDRadarProcessor(station_code="srt")

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


def test_surat_thani_legitimate_rain_detected():
    """Verify that legitimate rain green and yellow colors are accurately detected for Surat Thani."""
    processor = TMDRadarProcessor(station_code="srt")

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
