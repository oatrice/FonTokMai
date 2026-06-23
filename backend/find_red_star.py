import cv2
import numpy as np

img = cv2.imread('/Users/oatrice/Documents/2569-06-23 13.32.31.jpg')

# Convert to HSV to find red
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
lower_red1 = np.array([0, 100, 100])
upper_red1 = np.array([10, 255, 255])
lower_red2 = np.array([160, 100, 100])
upper_red2 = np.array([180, 255, 255])

mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
mask = mask1 | mask2

y, x = np.where(mask)
if len(y) > 0:
    print(f"Red pixels found around: x={np.mean(x):.1f}, y={np.mean(y):.1f}")
else:
    print("No red pixels found in HSV range")
