import numpy as np
from app.services.tmd_radar.clustering import TMDClusteringMixin
from app.services.tmd_radar_config import DBZ_COLOR_MAPPING

data = np.load('backend/tests/test_kkn240_frames.npz')
frames = data['frames']
img = frames[-1]

# 1. Count pixels using _get_dbz_at_pixel_static
count_static = 0
for y in range(80, 720):
    for x in range(80, 720):
        dbz = TMDClusteringMixin._get_dbz_at_pixel_static(img, x, y)
        if dbz >= 10.0:
            count_static += 1

# 2. Count pixels using extract_rain_mask
mask = TMDClusteringMixin().extract_rain_mask(img)
count_mask = np.sum((mask >= 40) & (np.fromfunction(lambda y, x: (x >= 80) & (x < 720) & (y >= 80) & (y < 720), img.shape[:2])))

print(f"Static count (80-720): {count_static}")
print(f"Mask count (80-720): {count_mask}")

# 3. Mask count without hysteresis (80-720)
mask_no_hyst = clean_mask
count_no_hyst = np.sum((mask_no_hyst >= 40) & (np.fromfunction(lambda y, x: (x >= 80) & (x < 720) & (y >= 80) & (y < 720), img.shape[:2])))
print(f"Mask count without hysteresis (80-720): {count_no_hyst}")
