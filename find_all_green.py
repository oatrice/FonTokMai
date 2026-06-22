import cv2
import numpy as np

img = cv2.imread("current_skn.jpg")
b, g, r = cv2.split(img)

mask_green = (g > 120) & (g > r + 30) & (g > b + 30)
coords = np.argwhere(mask_green)

dist = np.sqrt((coords[:, 1] - 475)**2 + (coords[:, 0] - 349)**2)
close_clouds = coords[dist < 200]

if len(close_clouds) > 0:
    for y, x in close_clouds[::len(close_clouds)//5 + 1]:
        print(f"Cloud at {x}, {y} (dist: {np.sqrt((x-475)**2 + (y-349)**2):.1f} px)")
else:
    print("No green clouds near user")
