import urllib.request
import cv2
import numpy as np

req = urllib.request.urlopen("https://weather.tmd.go.th/skn/skn240_latest.jpg")
arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
img = cv2.imdecode(arr, -1)
print(f"Shape: {img.shape}")

# Also let's find the red circle if any, or just save a crop
# No need, just print shape
