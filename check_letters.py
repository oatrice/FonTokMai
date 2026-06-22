import cv2
import numpy as np
from app.services.tmd_radar_processor import TMDRadarProcessor

processor = TMDRadarProcessor("skn240")
img = cv2.imread("current_skn.jpg")
b, g, r = cv2.split(img)

# user_px, user_py = 537, 349
# Check a 10x10 area around it
for dy in range(-10, 11):
    for dx in range(-10, 11):
        sx = 537 + dx
        sy = 349 + dy
        d = processor.get_dbz_at_pixel(img, sx, sy)
        if d >= 10.0:
            print(f"Found {d} dBZ at {dx}, {dy} (color: {img[sy, sx]})")
