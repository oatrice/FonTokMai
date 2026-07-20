import numpy as np
import cv2
from app.services.tmd_radar.clustering import TMDClusteringMixin

data = np.load('backend/tests/test_kkn240_frames.npz')
frames = data['frames']
img = frames[-1]

mask = TMDClusteringMixin.extract_rain_mask(None, img)

y, x = np.where(mask > 0)
print(f"Total rain pixels: {len(x)}")
print(f"X range: {x.min()}-{x.max()}, Y range: {y.min()}-{y.max()}")
