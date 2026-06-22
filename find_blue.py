import cv2
import numpy as np

img = cv2.imread("/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/.tempmediaStorage/media_758941b4-7979-4dd6-9917-012a34e7d6c0_1782122488765.jpg")
b, g, r = cv2.split(img)
mask = (b > 200) & (g < 50) & (r < 50)
coords = np.argwhere(mask)
if len(coords) > 0:
    center_y = int(np.mean(coords[:, 0]))
    center_x = int(np.mean(coords[:, 1]))
    print(f"Blue Cross at: {center_x}, {center_y} (Image shape: {img.shape})")
else:
    print("No blue cross found")
