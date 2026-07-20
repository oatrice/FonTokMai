import numpy as np
import cv2
from app.services.tmd_radar.clustering import TMDClusteringMixin

data = np.load('backend/tests/test_kkn240_frames.npz')
frames = data['frames']
img = frames[-1]

mask = TMDClusteringMixin.extract_rain_mask(None, img)

# Let's see the old mask
old_mask = np.zeros(img.shape[:2], dtype=np.uint8)
img_float = img.astype(np.float32)
for color, dbz in {
    (0, 255, 255): 10.0,
    (0, 0, 255): 15.0,
    (0, 255, 0): 20.0,
}.items(): # just a sample
    pass

import sys
sys.exit(0)
