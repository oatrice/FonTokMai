import cv2
import numpy as np

img = cv2.imread('/Users/oatrice/Documents/2569-06-23 12.48.25.jpg')
# Find the black borders or any indicators of the actual frame
# Loop GIFs from TMD have specific features: time text at top left, etc.
# Let's find the green "Sakon Nakhon" text or similar bright pixels

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
_, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
y, x = np.where(thresh > 0)
print(f"White pixels bounding box: x_min={x.min()}, x_max={x.max()}, y_min={y.min()}, y_max={y.max()}")
