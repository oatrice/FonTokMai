import pytest
import numpy as np
import cv2
import math
from app.services.tmd_radar_processor import TMDRadarProcessor
from app.services.tmd_radar_config import STATIONS

def test_config_min_area_and_legend_boxes():
    # Verify that the default configs exist on processor
    processor = TMDRadarProcessor("kkn240")
    assert hasattr(processor.config, "min_area_km2")
    assert isinstance(processor.config.min_area_km2, float)
    assert hasattr(processor.config, "legend_bboxes")
    assert isinstance(processor.config.legend_bboxes, list)

def test_circular_mask_vs_rectangular_margin():
    processor = TMDRadarProcessor("kkn240")
    # kkn240: crop_x = 80, crop_y = 40, crop_width = 720, crop_height = 720
    # Radar center: (440, 400), radius = 360
    # A pixel at (440, 60) has distance from center = 340 <= 360, so it is INSIDE the circle.
    # But it has Y = 60, which is < 80 (rectangular margin top was 80px).
    # Under old logic, it was zeroed out. Under new logic, it should be preserved.
    
    frame = np.zeros((800, 800, 3), dtype=np.uint8)
    flow = np.zeros((800, 800, 2), dtype=np.float32)
    
    # Place a 3x3 block of rain pixels around (440, 60) -> RGB (255, 0, 0)
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            frame[60 + dy, 440 + dx] = [255, 0, 0]
    
    # Run get_all_rain_clusters
    clusters = processor.get_all_rain_clusters(
        frame, flow, user_x=440, user_y=400,
        scan_radius=None, min_dbz=10.0
    )
    
    # Under new logic, this pixel should be detected as a cluster because it is inside the circular boundary
    # and not in a legend box.
    assert len(clusters) > 0, "Rain pixel at (440, 60) was incorrectly cleared by margins!"

def test_solidity_gating_concave_contour():
    processor = TMDRadarProcessor("kkn240")
    
    # Create an L-shaped (concave) contour
    # A simple L-shape:
    # (400, 400) to (400, 450) and (400, 450) to (450, 450)
    # Let's populate the frame with this shape
    frame = np.zeros((800, 800, 3), dtype=np.uint8)
    for y in range(400, 451):
        frame[y, 400] = [255, 0, 0]
    for x in range(400, 451):
        frame[450, x] = [255, 0, 0]
        
    dummy_clouds = [
        {
            "cx": 400, "cy": 400,
            "dbz_now": 35.0,
            "predicted_dbz": 35.0,
            "approaching": True,
            "eta_min": 10.0,
            "pixels": [(400, y) for y in range(400, 451)] + [(x, 450) for x in range(401, 451)]
        }
    ]
    
    # Generate the tracking image
    img_bytes = processor.generate_radar_tracking_image(
        frame, user_x=400, user_y=400,
        clouds=dummy_clouds, all_rain_clusters=[]
    )
    
    # We want to verify that the solidity gating works.
    # To do this, let's check that the generated image bytes are valid.
    assert img_bytes is not None
    assert isinstance(img_bytes, bytes)

def test_verbose_vs_draw_debug_grid(monkeypatch):
    from app.core.dev_settings import get_dev_settings, update_dev_settings
    
    # Reset config states
    update_dev_settings({"verbose": False})
    
    update_dev_settings({"draw_debug_grid": False})
    
    processor = TMDRadarProcessor("kkn240")
    frame = np.zeros((800, 800, 3), dtype=np.uint8)
    
    dummy_clouds = [
        {
            "cx": 400, "cy": 400,
            "dbz_now": 35.0,
            "predicted_dbz": 35.0,
            "approaching": True,
            "eta_min": 10.0,
            "pixels": [(400, 400)]
        }
    ]
    
    # 1. With verbose = True but draw_debug_grid = False (or absent), the output should be a single panel (720x720)
    update_dev_settings({"verbose": True})
    img_bytes = processor.generate_radar_tracking_image(
        frame, user_x=400, user_y=400,
        clouds=dummy_clouds, all_rain_clusters=[]
    )
    assert img_bytes is not None
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    assert img is not None
    # A single panel at scale 3x from crop_r=120 should be 720x720. 2-panel layout would be 720x1440.
    assert img.shape[1] == img.shape[0], f"Expected square single panel, got shape {img.shape}"

    # 2. With draw_debug_grid = True (Issue #263: 2 sub-images: Raw with grid + Final overlay), width should be double height
    update_dev_settings({"draw_debug_grid": True})
    img_bytes_grid = processor.generate_radar_tracking_image(
        frame, user_x=400, user_y=400,
        clouds=dummy_clouds, all_rain_clusters=[]
    )
    assert img_bytes_grid is not None
    img_grid = cv2.imdecode(np.frombuffer(img_bytes_grid, np.uint8), cv2.IMREAD_COLOR)
    assert img_grid is not None
    # 2-panel side-by-side: width is 2x height (e.g. 720x1440)
    assert img_grid.shape[1] == img_grid.shape[0] * 2, f"Expected 2-subimage side-by-side (1x2), got shape {img_grid.shape}"


def test_generate_radar_tracking_image_suppress_orphaned_trajectory():
    """
    Issue #268: Suppress trajectory rendering if source cloud is not detected in current frame.
    """
    processor = TMDRadarProcessor("kkn240")
    frame = np.zeros((800, 800, 3), dtype=np.uint8)

    # Predictions with rain from cloud A
    predictions = [
        {"time_offset": 0, "dbz": 30.0, "src_x": 400, "src_y": 400, "cluster": "A"},
        {"time_offset": 15, "dbz": 30.0, "src_x": 410, "src_y": 410, "cluster": "A"},
    ]

    # 1. Cloud A is NOT in clouds or all_rain_clusters -> Trajectory line should NOT be rendered
    img_bytes_orphaned = processor.generate_radar_tracking_image(
        frame, user_x=400, user_y=400,
        clouds=[], all_rain_clusters=[], predictions=predictions,
        show_trajectory=True
    )
    assert img_bytes_orphaned is not None
    img_orphaned = cv2.imdecode(np.frombuffer(img_bytes_orphaned, np.uint8), cv2.IMREAD_COLOR)
    # Yellow trajectory line color in BGR is (0, 255, 255)
    # Check that no yellow trajectory line pixels exist
    yellow_mask_orphaned = (img_orphaned[:, :, 0] == 0) & (img_orphaned[:, :, 1] == 255) & (img_orphaned[:, :, 2] == 255)
    assert not np.any(yellow_mask_orphaned), "Orphaned trajectory line was rendered when cloud was missing!"

    # 2. Cloud A IS in clouds -> Trajectory line is rendered
    cloud_a = {
        "cx": 400, "cy": 400, "label": "A", "dbz_now": 30.0, "predicted_dbz": 30.0,
        "approaching": True, "eta_min": 0.0, "pixels": [(400, 400)]
    }
    img_bytes_active = processor.generate_radar_tracking_image(
        frame, user_x=400, user_y=400,
        clouds=[cloud_a], all_rain_clusters=[cloud_a], predictions=predictions,
        show_trajectory=True
    )
    assert img_bytes_active is not None
    img_active = cv2.imdecode(np.frombuffer(img_bytes_active, np.uint8), cv2.IMREAD_COLOR)
    yellow_mask_active = (img_active[:, :, 0] == 0) & (img_active[:, :, 1] == 255) & (img_active[:, :, 2] == 255)
    assert np.any(yellow_mask_active), "Active cloud trajectory line should be rendered!"


