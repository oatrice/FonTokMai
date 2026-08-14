import numpy as np
import pytest
from app.services.tmd_radar.processor import TMDRadarProcessor
from app.services.tmd_radar.clustering import TMDClusteringMixin

def test_rayong_terrain_green_not_detected_as_rain():
    processor = TMDRadarProcessor(station_code="ryg")

    # Ground background terrain greens sampled from ryg_latest.jpg & TMD map background
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
        (0, 148, 11),
        (3, 155, 0),
        (32, 157, 57),
        (115, 171, 100),
        (105, 169, 95),
        (6, 128, 7),
        (5, 106, 0),
        (1, 114, 10),
        (62, 160, 23),
        (58, 139, 34),
        (50, 138, 34),
        (47, 152, 23),
        (62, 143, 40),
    ]

    img = np.zeros((10, 10, 3), dtype=np.uint8)

    for color in terrain_colors:
        img[5, 5] = color
        dbz = processor.get_dbz_at_pixel(img, x=5, y=5)
        assert dbz == 0.0, f"Terrain green color {color} was wrongly detected as {dbz} dBZ in scalar get_dbz_at_pixel"

    # Test vectorized _extract_raw_dbz_map and extract_rain_mask
    mixin = TMDClusteringMixin()
    for color in terrain_colors:
        test_frame = np.full((20, 20, 3), color, dtype=np.uint8)
        raw_map = mixin._extract_raw_dbz_map(test_frame)
        mask = mixin.extract_rain_mask(test_frame)
        assert np.max(raw_map) == 0.0, f"Vectorized _extract_raw_dbz_map failed for terrain color {color}"
        assert np.max(mask) == 0, f"Vectorized extract_rain_mask failed for terrain color {color}"


def test_real_rain_green_is_detected():
    processor = TMDRadarProcessor(station_code="ryg")

    # Real TMD radar rain greens (bright, saturated green)
    rain_colors = [
        (0, 255, 0),
        (4, 248, 3),
        (13, 239, 13),
        (36, 212, 41),
        (81, 212, 89),
        (5, 174, 5),
        (14, 171, 4),
    ]

    img = np.zeros((10, 10, 3), dtype=np.uint8)

    for color in rain_colors:
        img[5, 5] = color
        dbz = processor.get_dbz_at_pixel(img, x=5, y=5)
        assert dbz >= 20.0, f"Real rain green color {color} was wrongly ignored as {dbz} dBZ"

    mixin = TMDClusteringMixin()
    for color in rain_colors:
        test_frame = np.full((20, 20, 3), color, dtype=np.uint8)
        raw_map = mixin._extract_raw_dbz_map(test_frame)
        assert np.max(raw_map) >= 20.0, f"Vectorized _extract_raw_dbz_map missed rain color {color}"
