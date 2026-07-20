import numpy as np

data = np.load('backend/tests/test_kkn240_frames.npz')
frames = data['frames']
img = frames[-1]

coords = [(100, 100), (700, 700), (200, 500), (600, 200), (100, 600)]
for x, y in coords:
    rgb = img[y, x]
    print(f"BG at ({x}, {y}): RGB={list(rgb)}")
