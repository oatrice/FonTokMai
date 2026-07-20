import numpy as np
import cv2
from app.services.tmd_radar.clustering import TMDClusteringMixin

data = np.load('backend/tests/test_kkn240_frames.npz')
frames = data['frames']
img = frames[-1]

def extract_clean(img):
    img_float = img.astype(np.float32)
    from app.services.tmd_radar_config import DBZ_COLOR_MAPPING, IGNORED_COLORS
    min_dists = np.full(img.shape[:2], 25.0, dtype=np.float32)
    best_intensity = np.zeros(img.shape[:2], dtype=np.uint8)
    
    ignored_min_dists = np.full(img.shape[:2], float('inf'), dtype=np.float32)
    for ic in IGNORED_COLORS:
        ic_arr = np.array(ic, dtype=np.float32)
        dist = np.sqrt(np.sum((img_float - ic_arr)**2, axis=-1))
        better_mask = dist < ignored_min_dists
        ignored_min_dists[better_mask] = dist[better_mask]
        
    for color, dbz in DBZ_COLOR_MAPPING.items():
        c_arr = np.array(color, dtype=np.float32)
        dist = np.sqrt(np.sum((img_float - c_arr)**2, axis=-1))
        valid_mask = dist < ignored_min_dists
        better_mask = (dist < min_dists) & valid_mask
        min_dists[better_mask] = dist[better_mask]
        intensity = int(min(255, max(50, dbz * 4)))
        best_intensity[better_mask] = intensity
    return cv2.medianBlur(best_intensity, 3)

clean_mask = extract_clean(img)
count_no_hyst = np.sum((clean_mask >= 40) & (np.fromfunction(lambda y, x: (x >= 80) & (x < 720) & (y >= 80) & (y < 720), img.shape[:2])))
print(f"Mask count without hysteresis (80-720): {count_no_hyst}")
