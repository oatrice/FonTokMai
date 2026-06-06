import cv2
import numpy as np

img = cv2.imread("tests/tracking_test.png")
# Find green circle (the fake cloud)
green_mask = cv2.inRange(img, (0, 200, 0), (50, 255, 50))
green_y, green_x = np.where(green_mask > 0)
print(f"Fake cloud center: {np.mean(green_x)}, {np.mean(green_y)}")

# Find orange/red circle (the tracking circle drawn by generate_radar_tracking_image)
# The color is (0, 165, 255) for 50 dbz
track_mask = cv2.inRange(img, (0, 150, 240), (20, 180, 255))
track_y, track_x = np.where(track_mask > 0)
print(f"Tracking circle center: {np.mean(track_x)}, {np.mean(track_y)}")

# Are they the same?
