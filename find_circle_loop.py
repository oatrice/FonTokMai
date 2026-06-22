import urllib.request
import cv2
import numpy as np

req = urllib.request.urlopen("https://weather.tmd.go.th/skn/skn240Loop.gif")
arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
img = cv2.imdecode(arr, -1)

# Convert to grayscale
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
# Apply Gaussian blur
gray_blurred = cv2.GaussianBlur(gray, (9, 9), 2)
# Use HoughCircles
circles = cv2.HoughCircles(
    gray_blurred, 
    cv2.HOUGH_GRADIENT, 
    dp=1, 
    minDist=50, 
    param1=50, 
    param2=30, 
    minRadius=200, 
    maxRadius=400
)

if circles is not None:
    circles = np.uint16(np.around(circles))
    for i in circles[0, :]:
        print(f"Circle found at Center (x, y): ({i[0]}, {i[1]}), Radius: {i[2]}")
else:
    print("No circles found.")
