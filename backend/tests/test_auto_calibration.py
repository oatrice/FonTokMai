# backend/tests/test_auto_calibration.py

import os
import cv2
import numpy as np
import pytest
from app.services.tmd_radar.auto_calibration import AutoCalibrationService

def test_detect_radar_circle_synthetic():
    """Test Hough circle detection on a synthetic image containing a drawn circle."""
    service = AutoCalibrationService()
    # Create 800x800 white image
    img = np.ones((800, 800, 3), dtype=np.uint8) * 255
    # Draw black circle near center (cx=400, cy=400, r=300)
    cv2.circle(img, (400, 400), 300, (0, 0, 0), 4)

    circle = service.detect_radar_circle(img)
    assert circle is not None
    cx, cy, r = circle
    assert abs(cx - 400) <= 10
    assert abs(cy - 400) <= 10
    assert abs(r - 300) <= 10

def test_calculate_crops():
    """Test static and loop crop calculation logic."""
    service = AutoCalibrationService()
    img_shape = (800, 800, 3)
    circle = (400, 400, 300) # cx=400, cy=400, r=300 -> crop box x=100, y=100, w=600, h=600

    # Test without loop shape (1:1 ratio)
    crops = service.calculate_crops(img_shape, circle)
    padding = 10
    assert crops["static_crop_x"] == 100 - padding
    assert crops["static_crop_y"] == 100 - padding
    assert crops["static_crop_width"] == 600 + padding * 2
    assert crops["static_crop_height"] == 600 + padding * 2
    assert crops["loop_crop_x"] == 100 - padding
    assert crops["loop_crop_y"] == 100 - padding
    assert crops["loop_crop_width"] == 600 + padding * 2
    assert crops["loop_crop_height"] == 600 + padding * 2

    # Test with loop shape scaling (e.g. static is 800x800, loop is 400x400)
    loop_shape = (400, 400, 3)
    crops = service.calculate_crops(img_shape, circle, loop_shape)
    assert crops["loop_crop_x"] == (100 - padding) // 2
    assert crops["loop_crop_y"] == (100 - padding) // 2
    assert crops["loop_crop_width"] == (600 + padding * 2) // 2
    assert crops["loop_crop_height"] == (600 + padding * 2) // 2

def test_generate_config_snippet():
    """Test generating python StationConfig code snippet."""
    service = AutoCalibrationService()
    crop_info = {
        "static_crop_x": 100, "static_crop_y": 100, "static_crop_width": 600, "static_crop_height": 600,
        "loop_crop_x": 50, "loop_crop_y": 50, "loop_crop_width": 300, "loop_crop_height": 300
    }
    snippet = service.generate_config_snippet(
        code="cmi240",
        name="Chiang Mai (240km)",
        static_url="https://weather.tmd.go.th/cmi/cmi240_latest.jpg",
        loop_page_url="https://weather.tmd.go.th/cmiLoop.php",
        loop_gif_url="https://weather.tmd.go.th/cmi/cmi240_loop.gif",
        lat=18.77,
        lng=98.96,
        radius_km=240.0,
        crop_info=crop_info
    )

    assert "CMI240_BBOX = BoundingBox" in snippet
    assert '"cmi240": StationConfig(' in snippet
    assert 'static_crop_x=100' in snippet
    assert 'loop_crop_x=50' in snippet

def test_draw_crop_preview_and_base64():
    """Test drawing crop overlay and converting to base64 jpeg data URL."""
    service = AutoCalibrationService()
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    preview = service.draw_crop_preview(img, 50, 50, 200, 200, circle=(200, 200, 100))
    assert preview.shape == img.shape

    b64 = service.to_base64_jpeg(preview)
    assert b64.startswith("data:image/jpeg;base64,")

def test_cli_auto_calibrate_verify(tmp_path, monkeypatch):
    """Test CLI script invocation with --verify flag generating output image."""
    from unittest.mock import patch, MagicMock
    import scripts.calibrate_station_cli as cli

    # Create synthetic image bytes
    img = np.ones((800, 800, 3), dtype=np.uint8) * 255
    cv2.circle(img, (400, 400), 300, (0, 0, 0), 4)
    _, img_bytes = cv2.imencode(".jpg", img)

    out_file = str(tmp_path / "verify.jpg")
    test_args = [
        "calibrate_station_cli.py",
        "--code", "test240",
        "--name", "Test Radar (240km)",
        "--url", "https://weather.tmd.go.th/test/test240_latest.jpg",
        "--lat", "13.68",
        "--lng", "100.74",
        "--verify",
        "--output_image", out_file
    ]

    mock_resp = MagicMock()
    mock_resp.read.return_value = img_bytes.tobytes()
    mock_resp.__enter__.return_value = mock_resp

    with patch("sys.argv", test_args), patch("urllib.request.urlopen", return_value=mock_resp):
        cli.main()

    assert os.path.exists(out_file)
    assert os.path.getsize(out_file) > 0

