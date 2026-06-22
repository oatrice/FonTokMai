import cv2
import numpy as np

img = cv2.imread("/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/.tempmediaStorage/media_758941b4-7979-4dd6-9917-012a34e7d6c0_1782122488765.jpg")

# The app draws a WHITE halo first:
# cv2.circle(..., radius=20, color=(255,255,255))
# Then a BLUE circle and cross. But since Telegram converts it to JPEG, colors might slightly differ.
# Let's search for a dense cluster of white pixels followed by blue pixels in the center.

b, g, r = cv2.split(img)
# In the Telegram screenshot, the blue is very pure: R < 50, G < 50, B > 200
mask_blue = (b > 150) & (g < 100) & (r < 100)
coords = np.argwhere(mask_blue)

centers = []
for coord in coords:
    y, x = coord
    # Check if there is a white pixel nearby
    if np.any((b[y-10:y+10, x-10:x+10] > 200) & (g[y-10:y+10, x-10:x+10] > 200) & (r[y-10:y+10, x-10:x+10] > 200)):
        centers.append((x, y))

if len(centers) > 0:
    centers = np.array(centers)
    print(f"Blue cross center (with white halo): {int(np.mean(centers[:,0]))}, {int(np.mean(centers[:,1]))}")
else:
    print("No blue cross found")
