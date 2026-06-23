import cv2
import numpy as np

img = cv2.imread('test_frame0.png')
# find brightest pixels
mask = (img[:,:,0] > 240) & (img[:,:,1] > 240) & (img[:,:,2] > 240)
mask[:300, :] = 0
mask[400:, :] = 0
y, x = np.where(mask)
if len(x) > 0:
    print(f"Bright pixels at: X_min={x.min()}, X_max={x.max()}, Y_min={y.min()}, Y_max={y.max()}")
else:
    print("No bright pixels found")
