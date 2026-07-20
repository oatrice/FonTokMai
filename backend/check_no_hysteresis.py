import numpy as np
import cv2
import math
from app.services.tmd_radar.clustering import TMDClusteringMixin

# Let's run get_all_rain_clusters without weak colors
class TMDClusteringNoHysteresis(TMDClusteringMixin):
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
            
        return cv2.medianBlur(best_intensity, 3)

data = np.load('backend/tests/test_kkn240_frames.npz')
frames = data['frames']
img = frames[-1]
flow = data['flow']

cls = TMDClusteringNoHysteresis()
clusters = cls.get_all_rain_clusters(
    frame=img,
    flow=flow,
    user_x=486,
    user_y=390,
    scan_radius=None,
    min_dbz=10.0,
    cluster_dist=12,
    min_size=5
)

print("WITHOUT HYSTERESIS:")
for c in clusters:
    print(f"Cluster: cx={c['cx']}, cy={c['cy']}, size={c['size']}, dbz={c['dbz_now']}, bbox={c['xmin']}-{c['xmax']}, {c['ymin']}-{c['ymax']}")
