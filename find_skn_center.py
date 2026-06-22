import cv2
import numpy as np

img = cv2.imread("skn240_latest.jpg")
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Look for the radar center (the little crosshair or innermost circles)
# Or just use HoughCircles
circles = cv2.HoughCircles(
    gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=100,
    param1=50, param2=30, minRadius=300, maxRadius=400
)

if circles is not None:
    circles = np.round(circles[0, :]).astype("int")
    for (x, y, r) in circles:
        print(f"HoughCircle Center: {x}, {y}, r: {r}")

