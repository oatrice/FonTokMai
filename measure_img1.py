import cv2, numpy as np
img = cv2.imread('/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/user_img1.jpg')
mask_blue = (img[:, :, 0] > 200) & (img[:, :, 1] < 100) & (img[:, :, 2] < 100)
y_blue, x_blue = np.where(mask_blue)
if len(x_blue) > 0:
    print(f"user_img1 pin: {np.mean(x_blue)}, {np.mean(y_blue)}")
else:
    print("No pin found in user_img1")
