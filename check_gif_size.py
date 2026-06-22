import urllib.request
import cv2
import numpy as np

req = urllib.request.urlopen("https://weather.tmd.go.th/skn/skn240Loop.gif")
arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
img = cv2.imdecode(arr, -1)
print(f"skn240Loop.gif shape: {img.shape}")
