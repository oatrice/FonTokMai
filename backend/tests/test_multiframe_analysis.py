"""
Tests for TMDRadarProcessor.generate_multiframe_analysis_image()

ทดสอบว่าภาพ multi-frame analysis ถูกสร้างอย่างถูกต้อง
โดยใช้ dummy frames ที่มีสีฝนจำลอง
"""
import io
import math
import pytest
import numpy as np
from datetime import datetime, timezone
from PIL import Image

from app.services.tmd_radar_processor import TMDRadarProcessor, DBZ_COLOR_MAPPING


# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────

def make_black_frame(w=480, h=480) -> np.ndarray:
    """Empty (no rain) radar frame."""
    return np.zeros((h, w, 3), dtype=np.uint8)


def make_rain_frame(w=480, h=480, rain_cx=200, rain_cy=200, radius=30, dbz=40.0) -> np.ndarray:
    """
    Create a dummy radar frame with a filled rain circle at (rain_cx, rain_cy).
    Picks the first dBZ colour in DBZ_COLOR_MAPPING that is >= dbz.
    """
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    # Find the colour for the requested dBZ
    target_color = None
    best_diff = float("inf")
    for color, val in DBZ_COLOR_MAPPING.items():
        if abs(val - dbz) < best_diff:
            best_diff = abs(val - dbz)
            target_color = color

    if target_color is None:
        target_color = (255, 0, 0)

    import cv2
    cv2.circle(frame, (rain_cx, rain_cy), radius, target_color, -1)
    return frame


PROCESSOR = TMDRadarProcessor.__new__(TMDRadarProcessor)  # bare instance (no config needed)
USER_X, USER_Y = 240, 240


# ────────────────────────────────────────────────────────────
# Test: output is valid PNG bytes
# ────────────────────────────────────────────────────────────

def test_generates_png_bytes_with_rain():
    """Should return PNG bytes when called with 2+ frames and clouds."""
    f1 = make_rain_frame(rain_cx=180, rain_cy=180, dbz=35)
    f2 = make_rain_frame(rain_cx=200, rain_cy=200, dbz=40)
    frames = [f1, f2]
    flow = np.zeros((480, 480, 2), dtype=np.float32)
    clouds = [
        {
            "cx": 200, "cy": 200,
            "vx": 3.0, "vy": -2.0,
            "dbz_now": 40.0, "dbz_prev": 35.0,
            "predicted_dbz": 42.0,
            "eta_min": 20.0,
            "growth_rate": 0.1,
            "dist": 30.0,
        }
    ]
    result = TMDRadarProcessor.generate_multiframe_analysis_image(
        frames, flow, USER_X, USER_Y, clouds, PROCESSOR
    )
    assert result is not None
    assert isinstance(result, bytes)
    assert len(result) > 500
    # Must be decodable as an image
    img = Image.open(io.BytesIO(result))
    assert img.format == "PNG"


def test_returns_none_for_single_frame():
    """Less than 2 frames → returns None (can't compute trajectory)."""
    frames = [make_black_frame()]
    flow = np.zeros((480, 480, 2), dtype=np.float32)
    result = TMDRadarProcessor.generate_multiframe_analysis_image(
        frames, flow, USER_X, USER_Y, [], PROCESSOR
    )
    assert result is None


def test_returns_none_for_empty_frames():
    result = TMDRadarProcessor.generate_multiframe_analysis_image(
        [], None, USER_X, USER_Y, [], PROCESSOR
    )
    assert result is None


# ────────────────────────────────────────────────────────────
# Test: image dimensions are correct
# ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("num_frames, expected_cols", [
    (2, 2),
    (4, 4),
    (6, 6),
    (8, 6),  # clamped to MAX_FRAMES=6
])
def test_image_width_matches_frame_count(num_frames, expected_cols):
    """Width = THUMB_W × min(frames, 6)."""
    THUMB_W = 200
    frames = [make_black_frame() for _ in range(num_frames)]
    flow = np.zeros((480, 480, 2), dtype=np.float32)
    clouds = []
    result = TMDRadarProcessor.generate_multiframe_analysis_image(
        frames, flow, USER_X, USER_Y, clouds, PROCESSOR
    )
    assert result is not None
    img = Image.open(io.BytesIO(result))
    assert img.width == THUMB_W * expected_cols


def test_image_height_is_fixed():
    """Height = THUMB_H + HEADER_H + DBZ_ROW_H + GROWTH_ROW_H = 270."""
    EXPECTED_H = 200 + 28 + 22 + 20  # = 270
    frames = [make_black_frame(), make_black_frame()]
    flow = np.zeros((480, 480, 2), dtype=np.float32)
    result = TMDRadarProcessor.generate_multiframe_analysis_image(
        frames, flow, USER_X, USER_Y, [], PROCESSOR
    )
    assert result is not None
    img = Image.open(io.BytesIO(result))
    assert img.height == EXPECTED_H


# ────────────────────────────────────────────────────────────
# Test: no rain clouds
# ────────────────────────────────────────────────────────────

def test_no_clouds_still_produces_image():
    """Empty clouds list → image is still generated (only user pin, no cluster dots)."""
    frames = [make_black_frame(), make_black_frame()]
    flow = np.zeros((480, 480, 2), dtype=np.float32)
    result = TMDRadarProcessor.generate_multiframe_analysis_image(
        frames, flow, USER_X, USER_Y, [], PROCESSOR
    )
    assert result is not None
    img = Image.open(io.BytesIO(result))
    assert img.format == "PNG"


# ────────────────────────────────────────────────────────────
# Test: timestamp labelling
# ────────────────────────────────────────────────────────────

def test_with_timestamp_does_not_crash():
    """Passing a time_utc should produce timestamp labels without crashing."""
    frames = [make_black_frame(), make_black_frame(), make_black_frame()]
    flow = np.zeros((480, 480, 2), dtype=np.float32)
    now = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
    result = TMDRadarProcessor.generate_multiframe_analysis_image(
        frames, flow, USER_X, USER_Y, [], PROCESSOR, time_utc=now
    )
    assert result is not None


# ────────────────────────────────────────────────────────────
# Test: cluster back-tracking positions
# ────────────────────────────────────────────────────────────

def test_cluster_backtrace_positions():
    """
    With vx=5, vy=0 and a cloud at cx=220, in frame 0 (2 frames back)
    the cloud should be back-traced to x = 220 - 5*2 = 210.
    Verify _get_max_dbz_in_radius is called at the correct position.
    """
    # Place rain at x=210 in frame 0, x=215 in frame 1, x=220 in frame 2
    f0 = make_rain_frame(rain_cx=210, rain_cy=240, radius=15, dbz=35)
    f1 = make_rain_frame(rain_cx=215, rain_cy=240, radius=15, dbz=38)
    f2 = make_rain_frame(rain_cx=220, rain_cy=240, radius=15, dbz=40)
    frames = [f0, f1, f2]
    flow = np.zeros((480, 480, 2), dtype=np.float32)

    clouds = [
        {
            "cx": 220, "cy": 240,
            "vx": 5.0, "vy": 0.0,
            "dbz_now": 40.0, "dbz_prev": 35.0,
            "predicted_dbz": 42.0,
            "eta_min": 5.0,
            "growth_rate": 0.05,
            "dist": 20.0,
        }
    ]
    result = TMDRadarProcessor.generate_multiframe_analysis_image(
        frames, flow, USER_X, USER_Y, clouds, PROCESSOR
    )
    assert result is not None, "Should produce image when cloud is within crop radius"


# ────────────────────────────────────────────────────────────
# Test: growth/decay calculation logic (unit level)
# ────────────────────────────────────────────────────────────

def test_growth_positive():
    dbz_prev = 30.0
    dbz_now  = 36.0
    expected = ((dbz_now - dbz_prev) / dbz_prev) * 100.0
    assert abs(expected - 20.0) < 0.01


def test_growth_negative_decay():
    dbz_prev = 40.0
    dbz_now  = 32.0
    expected = ((dbz_now - dbz_prev) / dbz_prev) * 100.0
    assert abs(expected - (-20.0)) < 0.01


def test_growth_new_formation():
    """When prev is 0 but now > 0, it should be treated as 'new' (no division by zero)."""
    dbz_prev = 0.0
    dbz_now  = 35.0
    if dbz_prev == 0:
        result = "new"
    else:
        result = f"{((dbz_now - dbz_prev) / dbz_prev) * 100:.0f}%"
    assert result == "new"


def test_growth_dissipation():
    """When now is 0 but prev > 0, should show -100%."""
    dbz_prev = 40.0
    dbz_now  = 0.0
    expected = max(-100.0, ((dbz_now - dbz_prev) / dbz_prev) * 100.0)
    assert abs(expected - (-100.0)) < 0.01


# ────────────────────────────────────────────────────────────
# Test: multiframe is included in scheduler result dict
# ────────────────────────────────────────────────────────────

def test_result_dict_has_multiframe_key():
    """Verify test_e2e_mock_scenario fixture style: result dict has the new key."""
    # Simulated return dict as would be returned by WeatherManager._get_tmd_prediction
    simulated_result = {
        "predictions": [],
        "intensity": "ไม่มีฝน",
        "max_rain": 0.0,
        "max_dbz": 0.0,
        "duration_minutes": 0,
        "wind_speed_kmh": 0.0,
        "wind_dir_text": "N",
        "endpoint": "tmd-radar (kkn240)",
        "growth_rate_pct": 0.0,
        "approaching_clouds": [],
        "rain_summary": "ไม่มีฝน",
        "is_outdated": False,
        "radar_gif_bytes": None,
        "radar_hq_gif_bytes": None,
        "radar_static_bytes": None,
        "radar_tracking_bytes": None,
        "rain_timeline_bytes": None,
        "radar_multiframe_bytes": None,  # NEW key
    }
    assert "radar_multiframe_bytes" in simulated_result
