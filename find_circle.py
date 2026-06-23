import cv2
import numpy as np
import urllib.request

url = "https://weather.tmd.go.th/skn/skn240_latest.jpg"
req = urllib.request.urlopen(url)
arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
img = cv2.imdecode(arr, -1)

# The radar circle has a black border. Let's find the large circle.
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
edges = cv2.Canny(gray, 50, 150)
circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, 20, param1=50, param2=30, minRadius=200, maxRadius=400)
if circles is not None:
    circles = np.uint16(np.around(circles))
    for i in circles[0, :]:
        print(f"Circle found at cx={i[0]}, cy={i[1]} with radius={i[2]}")
else:
    print("No circles found.")
