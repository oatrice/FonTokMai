import cv2
import numpy as np

img = cv2.imread("/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/19_39_22.jpg")
print("Image shape:", img.shape)

# Let's find the red star (center of radar)
# Red star color is usually around (0, 0, 255) in BGR
lower_red = np.array([0, 0, 200])
upper_red = np.array([50, 50, 255])
mask = cv2.inRange(img, lower_red, upper_red)

# Find coordinates of red pixels
y, x = np.where(mask > 0)
if len(x) > 0:
    cx = int(np.mean(x))
    cy = int(np.mean(y))
    print(f"Red star found at px={cx}, py={cy}")
else:
    print("No red star found")
