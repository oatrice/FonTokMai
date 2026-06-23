import cv2
import numpy as np

img = cv2.imread('../test_raw_gif.png')
# Borders in TMD radar maps are usually pure white (255, 255, 255) or black.
# Let's check for white pixels near 404, 297.
mask = (img[:,:,0] > 240) & (img[:,:,1] > 240) & (img[:,:,2] > 240)
border_points = np.argwhere(mask)

if len(border_points) > 0:
    target = np.array([297, 404])
    distances = np.linalg.norm(border_points - target, axis=1)
    min_idx = np.argmin(distances)
    closest_border = border_points[min_idx]
    print(f"Closest white pixel: y={closest_border[0]}, x={closest_border[1]} (distance {distances[min_idx]:.1f} px)")
else:
    print("No white pixels found")

east_border = []
for x in range(404, min(img.shape[1], 600)):
    if mask[297, x]:
        east_border.append(x)
print(f"White pixels directly East: {east_border}")

north_border = []
for y in range(297, max(0, 200), -1):
    if mask[y, 404]:
        north_border.append(y)
print(f"White pixels directly North: {north_border}")
