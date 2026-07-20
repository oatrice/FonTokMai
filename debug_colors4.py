import numpy as np

data = np.load('backend/tests/test_kkn240_frames.npz', allow_pickle=True)
img = data['frames'][0] # Check first frame

pts = [(317, 6), (257, 92), (325, 68), (500, 675), (557, 687), (681, 220), (693, 162),
       (434, 415), (374, 416), (505, 363), (658, 505), (673, 527), (440, 470), (540, 660),
       (589, 657), (371, 414), (417, 420)]

for pt in pts:
    y, x = pt[0], pt[1]  
    try:
        print(f"Point {pt}: color at [y={y}, x={x}] is {img[y, x]}")
    except: pass
    try:
        print(f"Point {pt}: color at [x={x}, y={y}] is {img[x, y]}")
    except: pass

