import numpy as np
import cv2
import math
from app.services.tmd_radar.clustering import TMDClusteringMixin

class TMDClusteringSmallDilation(TMDClusteringMixin):
    def extract_rain_mask(self, img: np.ndarray) -> np.ndarray:
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
            
        # Hysteresis with smaller dilation (15x15)
        weak_colors = [(87, 96, 65), (69, 78, 47), (130, 145, 106)]
        weak_mask = np.zeros(img.shape[:2], dtype=bool)
        for wc in weak_colors:
            wc_arr = np.array(wc, dtype=np.float32)
            dist = np.sqrt(np.sum((img_float - wc_arr)**2, axis=-1))
            weak_mask |= (dist < 15.0)
            
        if np.any(weak_mask):
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
            dilated_strong = cv2.dilate(best_intensity, kernel)
            valid_weak = weak_mask & (dilated_strong > 0)
            best_intensity[valid_weak] = max(50, int(15.0 * 4))
            
        return cv2.medianBlur(best_intensity, 3)

data = np.load('backend/tests/test_kkn240_frames.npz')
frames = data['frames']
img = frames[-1]
flow = data['flow']

cls = TMDClusteringSmallDilation()
clusters = cls.get_all_rain_clusters(img, flow, 486, 390)
print("WITH 15x15 DILATION:")
for c in clusters:
    if c['size'] > 1000:
        print(f"Cluster: cx={c['cx']}, cy={c['cy']}, size={c['size']}, dbz={c['dbz_now']}, bbox={c['xmin']}-{c['xmax']}, {c['ymin']}-{c['ymax']}")
