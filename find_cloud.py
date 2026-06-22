import cv2
import numpy as np

img = cv2.imread("current_skn.jpg")
b, g, r = cv2.split(img)

# Green clouds: G > 150, R < 100, B < 100
mask_green = (g > 150) & (r < 100) & (b < 100)
coords = np.argwhere(mask_green)

# Find green clouds near 475, 349
dist = np.sqrt((coords[:, 1] - 475)**2 + (coords[:, 0] - 349)**2)
close_clouds = coords[dist < 150]

if len(close_clouds) > 0:
    for y, x in close_clouds[::len(close_clouds)//5 + 1]:
        print(f"Cloud at {x}, {y} (dist: {np.sqrt((x-475)**2 + (y-349)**2):.1f} px)")
else:
    print("No green clouds near user")
