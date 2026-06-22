import cv2
import numpy as np

img = cv2.imread("test_user_image.jpg")
# The pin has color (0, 0, 255) in BGR? Wait, opencv uses BGR so red is (0, 0, 255).
# Let's find red/blue pixels.
b, g, r = cv2.split(img)
# Find pixels where red > 200 and blue < 50 and green < 50
mask_red = (r > 200) & (g < 50) & (b < 50)
coords_red = np.argwhere(mask_red)
if len(coords_red) > 0:
    center_y = int(np.mean(coords_red[:, 0]))
    center_x = int(np.mean(coords_red[:, 1]))
    print(f"Found RED pin at: {center_x}, {center_y}")

# The code draws a white halo too.
mask_blue = (b > 200) & (g < 50) & (r < 50)
coords_blue = np.argwhere(mask_blue)
if len(coords_blue) > 0:
    center_y = int(np.mean(coords_blue[:, 0]))
    center_x = int(np.mean(coords_blue[:, 1]))
    print(f"Found BLUE pin at: {center_x}, {center_y}")
