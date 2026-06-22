import cv2
import numpy as np
import math

DBZ_COLOR_MAPPING = {
    (0, 255, 0): 25.0,
    (0, 200, 0): 30.0,
    (0, 150, 0): 35.0,
    (255, 255, 0): 40.0,
    (255, 200, 0): 45.0,
    (255, 150, 0): 50.0,
    (255, 0, 0): 55.0,
    (200, 0, 0): 60.0,
    (150, 0, 0): 65.0,
}
IGNORED_COLORS = [
    (255, 255, 255), (0, 0, 0), (204, 204, 204),
    (32, 45, 93), (153, 153, 153),
    (54, 114, 156), # River light blue (guess)
]

def get_dbz(r, g, b, threshold):
    min_dist_dbz = float('inf')
    best_dbz = 0.0
    for color, dbz in DBZ_COLOR_MAPPING.items():
        dist = math.sqrt((r - color[0])**2 + (g - color[1])**2 + (b - color[2])**2)
        if dist < min_dist_dbz:
            min_dist_dbz = dist
            best_dbz = dbz
    
    min_dist_ignored = float('inf')
    for color in IGNORED_COLORS:
        dist = math.sqrt((r - color[0])**2 + (g - color[1])**2 + (b - color[2])**2)
        if dist < min_dist_ignored:
            min_dist_ignored = dist
            
    if min_dist_ignored <= min_dist_dbz:
        return 0.0
        
    if min_dist_dbz < threshold:
        return best_dbz
    return 0.0

# Simulate a noisy river or text edge pixel
print("Testing dark blue/green:")
print("R=50, G=150, B=100 (Threshold 40):", get_dbz(50, 150, 100, 40))
print("R=50, G=150, B=100 (Threshold 25):", get_dbz(50, 150, 100, 25))

print("Testing pure rain:")
print("R=0, G=240, B=10 (Threshold 40):", get_dbz(0, 240, 10, 40))
print("R=0, G=240, B=10 (Threshold 25):", get_dbz(0, 240, 10, 25))
