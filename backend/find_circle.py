import cv2
import numpy as np

img = cv2.imread('../test_raw_gif.png')
for x in range(340):
    if np.any(img[340, x] > 50): # non-dark
        print(f"Left edge at x={x}")
        break

for x in range(679, 340, -1):
    if np.any(img[340, x] > 50):
        print(f"Right edge at x={x}")
        break
