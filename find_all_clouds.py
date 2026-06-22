import cv2
import numpy as np

img = cv2.imread("current_skn.jpg")
b, g, r = cv2.split(img)

mask_green = (g > 150) & (r < 100) & (b < 100)
coords = np.argwhere(mask_green)

if len(coords) > 0:
    for y, x in coords[::len(coords)//10 + 1]:
        print(f"Cloud at {x}, {y}")
else:
    print("No green clouds")
