import cv2, numpy as np

img = cv2.imread('/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/frame0.png')
# Look for the white square. 
# It's usually exactly 255,255,255
mask = (img[:, :, 0] > 240) & (img[:, :, 1] > 240) & (img[:, :, 2] > 240)
y, x = np.where(mask)
for ix, iy in zip(x, y):
    # Only squares surrounded by dark pixels
    pass
