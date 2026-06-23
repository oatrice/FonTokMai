import cv2, numpy as np

img = cv2.imread('/Users/oatrice/Documents/2569-06-23 12.48.25.jpg')
mask_blue = (img[:,:,0] > 200) & (img[:,:,2] < 100)
y, x = np.where(mask_blue)
if len(x) > 0:
    print(f"Pin found at X={int(np.mean(x))}, Y={int(np.mean(y))}")
else:
    print("Pin not found")
