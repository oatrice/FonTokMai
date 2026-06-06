import cv2
import numpy as np
from app.services.tmd_radar_processor import TMDRadarProcessor

processor = TMDRadarProcessor("kkn120")
frame = np.zeros((680, 680, 3), dtype=np.uint8)
user_x, user_y = 50, 50

# Cloud at 20, 20
cv2.circle(frame, (20, 20), 10, (0, 255, 0), -1)

clouds = [{
    "cx": 20, "cy": 20,
    "vx": 4, "vy": 4,
    "eta_min": 10,
    "predicted_dbz": 50
}]

img_bytes = processor.generate_radar_tracking_image(frame, user_x, user_y, clouds)
with open("tests/tracking_test2.png", "wb") as f:
    f.write(img_bytes)

img = cv2.imread("tests/tracking_test2.png")
green_mask = cv2.inRange(img, (0, 200, 0), (50, 255, 50))
green_y, green_x = np.where(green_mask > 0)
print(f"Fake cloud center: {np.mean(green_x)}, {np.mean(green_y)}")

track_mask = cv2.inRange(img, (0, 150, 240), (20, 180, 255))
track_y, track_x = np.where(track_mask > 0)
print(f"Tracking circle center: {np.mean(track_x)}, {np.mean(track_y)}")
