import cv2
import numpy as np

img = cv2.imread("/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/.tempmediaStorage/media_758941b4-7979-4dd6-9917-012a34e7d6c0_1782122488765.jpg")

for dy in [-20, -10, 0, 10, 20]:
    for dx in [-20, -10, 0, 10, 20]:
        sx = 537 + dx
        sy = 349 + dy
        c = img[sy, sx].astype(np.float32) # BGR
        dist = np.sqrt((c[2] - 0)**2 + (c[1] - 255)**2 + (c[0] - 0)**2)
        print(f"Offset {dx},{dy} - BGR: {c} - Dist to 25 dBZ: {dist:.1f}")

