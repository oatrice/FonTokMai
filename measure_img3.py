import cv2, numpy as np
img = cv2.imread('/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/user_img3.jpg')

# Find the blue pin center
mask_blue = (img[:, :, 0] > 200) & (img[:, :, 1] < 100) & (img[:, :, 2] < 100)
y_blue, x_blue = np.where(mask_blue)
pin_x = np.mean(x_blue)
pin_y = np.mean(y_blue)

# Find the white square for Sakon Nakhon
mask_white = (img[:, :, 0] > 240) & (img[:, :, 1] > 240) & (img[:, :, 2] > 240)
# We know Sakon Nakhon is on the left, so we filter x < pin_x
y_white, x_white = np.where(mask_white)
sq_x = []
sq_y = []
for ix, iy in zip(x_white, y_white):
    if ix < pin_x - 50:
        sq_x.append(ix)
        sq_y.append(iy)
print("Pin in user_img3:", pin_x, pin_y)
print("Sakon Nakhon in user_img3:", np.mean(sq_x), np.mean(sq_y))
