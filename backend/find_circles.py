import cv2
import numpy as np

img = cv2.imread('../test_raw_gif.png')
# Convert to gray
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
# Apply HoughCircles to find the radar circles!
circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, 100,
                           param1=50, param2=30, minRadius=100, maxRadius=400)

if circles is not None:
    circles = np.uint16(np.around(circles))
    for i in circles[0, :]:
        print(f"Circle center: ({i[0]}, {i[1]}), radius: {i[2]}")
else:
    print("No circles found")
