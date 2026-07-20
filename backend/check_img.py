import numpy as np
import cv2

data = np.load('backend/tests/test_kkn240_frames.npz')
frames = data['frames']
img = frames[-1]

mask = np.zeros(img.shape[:2], dtype=np.uint8)

colors_to_test = [
    (87, 96, 65),
    (69, 78, 47),
    (130, 145, 106),
]

for tgt in colors_to_test:
    diff = np.abs(img.astype(np.int32) - np.array(tgt))
    dist = np.sum(diff, axis=-1)
    mask[dist < 10] = 255

img_copy = img.copy()
img_copy[mask == 255] = [0, 0, 255] # Red

cv2.imwrite('backend/tests/test_faded_rain.png', img_copy)
