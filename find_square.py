import cv2, numpy as np

img = cv2.imread('/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/frame0.png')
# Look for a small pure white square
mask = (img[:, :, 0] > 240) & (img[:, :, 1] > 240) & (img[:, :, 2] > 240)
# We know Sakon Nakhon is near the center, x~380, y~300
y, x = np.where(mask)
for ix, iy in zip(x, y):
    if 300 < ix < 450 and 250 < iy < 350:
        print(f"White pixel at {ix}, {iy}")
