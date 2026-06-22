import cv2
import numpy as np

img = cv2.imread("test_home.jpg")
b, g, r = cv2.split(img)

# Find very bright red pixels
mask_red = (r > 200) & (g < 50) & (b < 50)
coords_red = np.argwhere(mask_red)
if len(coords_red) > 0:
    for y, x in coords_red[::len(coords_red)//10 + 1]:
        print(f"Red pixel at: {x}, {y}")

