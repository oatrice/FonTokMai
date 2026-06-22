import cv2
import numpy as np

img = cv2.imread("/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/.tempmediaStorage/media_758941b4-7979-4dd6-9917-012a34e7d6c0_1782122488765.jpg")

for dy in range(-20, 20, 5):
    for dx in range(-20, 20, 5):
        sx = 537 + dx
        sy = 349 + dy
        c = img[sy, sx].astype(np.float32) # BGR
        # Calculate distance to (R=73, G=160, B=71)
        dist = np.sqrt((c[2] - 73)**2 + (c[1] - 160)**2 + (c[0] - 71)**2)
        if dist < 25:
            print(f"Offset {dx},{dy} - BGR: {c} - Dist to (73, 160, 71): {dist:.1f}")

