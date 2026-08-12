# backend/tests/test_khon_kaen_radar.py

import pytest
from app.services.tmd_radar_config import STATIONS, BoundingBox
from app.services.tmd_radar_catalog import KNOWN_TMD_RADAR_PRESETS
from app.services.tmd_radar.processor import TMDRadarProcessor


def test_khon_kaen_station_registered():
    """Verify that 'kkn240' station is registered with exact calibrated crop offsets."""
    assert "kkn240" in STATIONS, "Station 'kkn240' missing from STATIONS dictionary"
    st = STATIONS["kkn240"]
    assert st.code == "kkn240"
    assert st.center_lat == 16.4023
    assert st.center_lng == 102.8672
    assert st.radius_km == 240.0
    assert st.static_crop_x == 71
    assert st.static_crop_y == 29
    assert st.static_crop_width == 724
    assert st.static_crop_height == 724
    assert st.loop_crop_x == 71
    assert st.loop_crop_y == 29
    assert st.loop_crop_width == 724
    assert st.loop_crop_height == 724

    kkn_preset = next((p for p in KNOWN_TMD_RADAR_PRESETS if p["code"] == "kkn240"), None)
    assert kkn_preset is not None, "Khon Kaen ('kkn240') preset missing from KNOWN_TMD_RADAR_PRESETS"
    assert st.static_crop_x == 71
    assert st.static_crop_y == 29
    assert st.static_crop_width == 724
    assert st.static_crop_height == 724
    assert st.loop_crop_x == 71
    assert st.loop_crop_y == 29


def test_khon_kaen_thabo_pin_pixel_location():
    """Regression test: Verify that Thabo, Nong Khai (17.8392, 102.5734) on kkn240
    resolves to exact pixel in 800x800 full frame coordinates
    and 724x724 cropped frame coordinates.
    """
    processor = TMDRadarProcessor(station_code="kkn240")

    # 1. Full 800x800 frame mapping
    px, py = processor.latlng_to_pixel(17.8392, 102.5734, is_loop=False)
    assert px is not None and py is not None

    # 2. Cropped 724x724 frame mapping (with frame_shape supplied)
    px_crop, py_crop = processor.latlng_to_pixel(17.8392, 102.5734, is_loop=False, frame_shape=(724, 724))
    assert px_crop == px - 71
    assert py_crop == py - 29


def test_khon_kaen_radar_center_pixel_location():
    """Verify that radar antenna center (16.4023, 102.8672) maps to center of 724x724 crop (362, 362)
    and physical crosshair (433, 391) on 800x800 image.
    """
    processor = TMDRadarProcessor(station_code="kkn240")

    # Full frame 800x800: center crosshair = (433, 391)
    px, py = processor.latlng_to_pixel(16.4023, 102.8672, is_loop=False)
    assert px == 433, f"Expected full frame center x=433, got {px}"
    assert py == 391, f"Expected full frame center y=391, got {py}"

    # Cropped frame 724x724: crop center = (362, 362)
    px_crop, py_crop = processor.latlng_to_pixel(16.4023, 102.8672, is_loop=True, frame_shape=(724, 724))
    assert px_crop == 362, f"Expected crop frame center x=362, got {px_crop}"
    assert py_crop == 362, f"Expected crop frame center y=362, got {py_crop}"
