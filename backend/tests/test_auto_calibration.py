# backend/tests/test_auto_calibration.py

import pytest
import numpy as np
import cv2
from app.services.tmd_radar.auto_calibration import AutoCalibrationService

def create_synthetic_radar_image(width=800, height=800, center=(400, 400), radius=350):
    """Creates a synthetic radar image with a dark background and a bright circle border."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    # Draw radar circle border (white/bright line)
    cv2.circle(img, center, radius, (255, 255, 255), 4)
    return img

def test_detect_radar_circle_synthetic():
    img = create_synthetic_radar_image(width=800, height=800, center=(400, 400), radius=350)
    service = AutoCalibrationService()
    
    circle = service.detect_radar_circle(img)
    assert circle is not None
    cx, cy, r = circle
    assert abs(cx - 400) <= 5
    assert abs(cy - 400) <= 5
    assert abs(r - 350) <= 5

def test_calculate_crops_from_circle():
    service = AutoCalibrationService()
    # Given detected circle (cx=400, cy=400, r=350) in an 800x800 image
    crop_info = service.calculate_crops(img_shape=(800, 800, 3), circle=(400, 400, 350), loop_shape=(680, 680, 3))
    
    assert crop_info["static_crop_x"] == 50
    assert crop_info["static_crop_y"] == 50
    assert crop_info["static_crop_width"] == 700
    assert crop_info["static_crop_height"] == 700

    # loop crop scaled proportionally (680 / 800 * 700 = 595, offset 680 / 800 * 50 = 42.5 -> 42/43)
    assert abs(crop_info["loop_crop_width"] - 595) <= 2
    assert abs(crop_info["loop_crop_height"] - 595) <= 2

def test_generate_station_config_snippet():
    service = AutoCalibrationService()
    snippet = service.generate_config_snippet(
        code="cmi240",
        name="Chiang Mai (240km)",
        static_url="https://weather.tmd.go.th/cmi/cmi240_latest.jpg",
        loop_page_url="https://weather.tmd.go.th/cmiLoop.php",
        loop_gif_url="https://weather.tmd.go.th/cmi/cmiloop.gif",
        lat=18.77,
        lng=98.97,
        radius_km=240.0,
        crop_info={
            "static_crop_x": 50,
            "static_crop_y": 50,
            "static_crop_width": 700,
            "static_crop_height": 700,
            "loop_crop_x": 42,
            "loop_crop_y": 42,
            "loop_crop_width": 595,
            "loop_crop_height": 595,
        }
    )
    assert '"cmi240": StationConfig(' in snippet
    assert 'center_lat=18.77' in snippet
    assert 'radius_km=240.0' in snippet
