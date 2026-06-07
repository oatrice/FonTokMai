import sys
import os
import cv2
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
from app.services.tmd_radar_processor import TMDRadarProcessor

processor = TMDRadarProcessor("kkn240")
img = np.zeros((1, 1, 3), dtype=np.uint8)
img[0, 0] = [93, 45, 32] # BGR
dbz = processor.get_dbz_at_pixel(img, 0, 0)
print(f"dBZ for [93, 45, 32] is {dbz}")
