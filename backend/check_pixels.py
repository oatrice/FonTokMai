import numpy as np
from app.services.tmd_radar_config import DBZ_COLOR_MAPPING, IGNORED_COLORS
import math

data = np.load('backend/tests/test_kkn240_frames.npz')
frames = data['frames']
img = frames[-1] # The last frame

points = [
    ("P1", 317, 6),
    ("P2", 257, 92),
    ("P3", 325, 68),
]

for name, x, y in points:
    pixel = img[y, x]
    r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
    
    min_dist_dbz = float('inf')
    best_dbz = 0.0
    for color, dbz in DBZ_COLOR_MAPPING.items():
        dist = math.sqrt((r - color[0])**2 + (g - color[1])**2 + (b - color[2])**2)
        if dist < min_dist_dbz:
            min_dist_dbz = dist
            best_dbz = dbz
            
    min_dist_ignored = float('inf')
    for ic in IGNORED_COLORS:
        dist = math.sqrt((r - ic[0])**2 + (g - ic[1])**2 + (b - ic[2])**2)
        if dist < min_dist_ignored:
            min_dist_ignored = dist
            
    print(f"{name} ({x}, {y}): RGB={r},{g},{b}")
    print(f"  Best DBZ: {best_dbz} (dist={min_dist_dbz:.1f})")
    print(f"  Best Ignored: (dist={min_dist_ignored:.1f})")
    
    if min_dist_ignored <= min_dist_dbz:
        print("  -> FILTERED (closer to ignored)")
    elif min_dist_dbz < 25:
        print(f"  -> KEPT (dBZ={best_dbz})")
    else:
        print("  -> FILTERED (dist >= 25)")
