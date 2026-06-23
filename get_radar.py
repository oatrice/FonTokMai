import cv2
import numpy as np
import urllib.request

url = "https://weather.tmd.go.th/skn/skn240_latest.jpg"
req = urllib.request.urlopen(url)
arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
img = cv2.imdecode(arr, -1)

print("Original image shape:", img.shape)

# Find the red star (center of radar)
lower_red = np.array([0, 0, 200])
upper_red = np.array([50, 50, 255])
mask = cv2.inRange(img, lower_red, upper_red)

y, x = np.where(mask > 0)
if len(x) > 0:
    cx = int(np.mean(x))
    cy = int(np.mean(y))
    print(f"Red star found at px={cx}, py={cy}")
else:
    print("No red star found")
