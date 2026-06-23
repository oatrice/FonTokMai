import cv2, numpy as np
img = cv2.imread('/Users/oatrice/Documents/2569-06-22 19.59.49.jpg')
mask = (img[:,:,0] >= 240) & (img[:,:,1] >= 240) & (img[:,:,2] >= 240)
mask[:200, :] = 0
mask[600:, :] = 0
kernel = np.ones((3,3), np.uint8)
solid = cv2.erode(mask.astype(np.uint8), kernel)
y, x = np.where(solid)
if len(x) > 0:
    print(f"Solid white square at X={int(np.mean(x))}, Y={int(np.mean(y))}")
