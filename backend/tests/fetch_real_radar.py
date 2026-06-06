import cv2
import numpy as np
import os
from app.services.tmd_radar_processor import TMDRadarProcessor

processor = TMDRadarProcessor("kkn120")

# Create a fake radar image (dark background)
frame = np.ones((680, 680, 3), dtype=np.uint8) * 30

# Draw fake map features (rivers/roads)
cv2.polylines(frame, [np.array([[100, 100], [200, 300], [400, 500], [600, 650]])], False, (100, 100, 100), 2)
cv2.polylines(frame, [np.array([[600, 100], [500, 200], [400, 200], [200, 400]])], False, (100, 100, 100), 2)

# Draw a large, blobby storm cell
center = (300, 300)
for radius in range(50, 0, -10):
    color = (0, 255, 0) # Green
    if radius <= 30: color = (0, 165, 255) # Orange
    if radius <= 10: color = (0, 0, 255) # Red
    cv2.circle(frame, center, radius, color, -1)

# Another smaller storm
center2 = (450, 250)
cv2.circle(frame, center2, 30, (0, 255, 0), -1)
cv2.circle(frame, center2, 15, (0, 165, 255), -1)

# User is located near the big storm, slightly offset
user_x, user_y = 260, 360

# Mock clouds exactly as they would come out of our BFS clustering
clouds = [
    {
        "cx": 300, "cy": 300,
        "vx": 8.0, "vy": -4.0, # moving right and up
        "eta_min": 25.0,
        "predicted_dbz": 55.0
    },
    {
        "cx": 450, "cy": 250,
        "vx": 6.0, "vy": -2.0,
        "eta_min": -5.0,
        "predicted_dbz": 45.0
    }
]

processor.draw_pin_on_frame(frame, user_x, user_y)
img_bytes = processor.generate_radar_tracking_image(frame, user_x, user_y, clouds)

out_path = os.path.join(os.getcwd(), "tests/synthetic_tracking_result.png")
with open(out_path, "wb") as f:
    f.write(img_bytes)
print(f"Saved {out_path}")
