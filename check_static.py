import cv2
import numpy as np

img = cv2.imread("backend/tmp/test_static.png")
if img is None:
    print("Failed to read image")
else:
    print(f"Image shape: {img.shape}")
    
    # The pin color is (0, 0, 255) in BGR which is RED, but wait, the drawing was done on RGB?
    # img_orig = Image.fromarray(cf) -> cf is RGB.
    # img_hq.save(buffer, format='PNG') -> saved as RGB.
    # cv2.imread loads it as BGR!
    # So the blue cross drawn as (0, 0, 255) RGB is saved as (0, 0, 255) RGB.
    # cv2 reads it as BGR, so the BGR value of (0, 0, 255) RGB is (255, 0, 0) BGR!
    # Let's search for (255, 0, 0) BGR (Blue).
    
    b, g, r = cv2.split(img)
    mask = (b > 200) & (g < 50) & (r < 50)
    coords = np.argwhere(mask)
    if len(coords) > 0:
        center_y = int(np.mean(coords[:, 0]))
        center_x = int(np.mean(coords[:, 1]))
        print(f"Blue pixels center: {center_x}, {center_y}")
    else:
        print("No blue pixels found!")
