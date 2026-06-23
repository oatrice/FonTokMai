import cv2
import numpy as np

img = cv2.imread('debug_pred_static.png')
# Find blue pixels (BGR: 255, 0, 0)
mask = (img[:,:,0] == 255) & (img[:,:,1] == 0) & (img[:,:,2] == 0)
y, x = np.where(mask)
if len(y) > 0:
    print(f"Pin found around: x={np.mean(x):.1f}, y={np.mean(y):.1f}")
    print(f"Divided by 3 (before resize): x={np.mean(x)/3:.1f}, y={np.mean(y)/3:.1f}")
else:
    print("No blue pin found")
