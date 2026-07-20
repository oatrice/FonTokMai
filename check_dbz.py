import cv2
import numpy as np
from app.services.tmd_radar_config import DBZ_COLOR_MAPPING, IGNORED_COLORS
from app.services.tmd_radar.clustering import TMDClusteringMixin

data = np.load("backend/tests/test_kkn240_frames.npz", allow_pickle=True)
frames = data["frames"]
last_frame = frames[-1]

pts = [(313, 26), (326, 68), (257, 91)]
for p in pts:
    max_d = 0
    for dy in range(-15, 16):
        for dx in range(-15, 16):
            sy, sx = p[1]+dy, p[0]+dx
            if 0 <= sx < last_frame.shape[1] and 0 <= sy < last_frame.shape[0]:
                d = TMDClusteringMixin._get_dbz_at_pixel_static(last_frame, sx, sy)
                if d > max_d: max_d = d
    print(f"Point {p}: Max dBZ in radius 15 = {max_d}")

