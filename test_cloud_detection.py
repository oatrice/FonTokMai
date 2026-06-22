import cv2
import numpy as np
from app.services.tmd_radar_processor import TMDRadarProcessor

processor = TMDRadarProcessor("skn240")
img = cv2.imread("current_skn.jpg")
b, g, r = cv2.split(img)

# Let's check the pixel values around 537, 349
y, x = 349, 537
roi_b = b[y-5:y+6, x-5:x+6]
roi_g = g[y-5:y+6, x-5:x+6]
roi_r = r[y-5:y+6, x-5:x+6]

print("R:")
print(roi_r)
print("G:")
print(roi_g)
print("B:")
print(roi_b)
