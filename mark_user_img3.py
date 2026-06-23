import cv2, numpy as np
img = cv2.imread('/Users/oatrice/Documents/2569-06-22 19.59.49.jpg')
# mark pin
mask_blue = (img[:,:,0] > 200) & (img[:,:,2] < 100)
y, x = np.where(mask_blue)
if len(x) > 0:
    cv2.circle(img, (int(np.mean(x)), int(np.mean(y))), 15, (0, 0, 255), 3)

# mark square
mask_white = (img[:,:,0] >= 240) & (img[:,:,1] >= 240) & (img[:,:,2] >= 240)
mask_white[:200, :] = 0
mask_white[600:, :] = 0
kernel = np.ones((3,3), np.uint8)
solid = cv2.erode(mask_white.astype(np.uint8), kernel)
y_sq, x_sq = np.where(solid)
if len(x_sq) > 0:
    cv2.circle(img, (int(np.mean(x_sq)), int(np.mean(y_sq))), 15, (0, 255, 0), 3)

cv2.imwrite('/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/marked_user_img3.jpg', img)
