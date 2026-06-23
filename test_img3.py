import cv2, numpy as np
img = cv2.imread('/Users/oatrice/Documents/2569-06-22 19.59.49.jpg')
# The pin is blue. Look for B > 200, R < 100
mask = (img[:,:,0] > 200) & (img[:,:,2] < 100)
y, x = np.where(mask)
if len(x) > 0:
    print(f"Pin found at X={int(np.mean(x))}, Y={int(np.mean(y))}")
else:
    print("Pin not found")
