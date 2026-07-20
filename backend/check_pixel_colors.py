import numpy as np

data = np.load('backend/tests/test_kkn240_frames.npz')
frames = data['frames']
img = frames[-1]

points = {
    "P1": (317, 6),
    "P2": (257, 92),
    "P3": (325, 68),
    "P4": (162, 693),
    "P5": (434, 415),
    "P6": (374, 416),
    "P7": (505, 363),
}

for name, (x, y) in points.items():
    if 0 <= x < img.shape[1] and 0 <= y < img.shape[0]:
        rgb = img[y, x]
        print(f"{name} at ({x}, {y}): RGB={list(rgb)}")
