import cv2
import numpy as np

img = cv2.imread('../temp_skn240_static.jpg')
mask = (img[:,:,0] > 240) & (img[:,:,1] > 240) & (img[:,:,2] > 240)
border_points = np.argwhere(mask)

if len(border_points) > 0:
    target = np.array([349, 475])
    distances = np.linalg.norm(border_points - target, axis=1)
    min_idx = np.argmin(distances)
    closest_border = border_points[min_idx]
    print(f"Closest white pixel: y={closest_border[0]}, x={closest_border[1]} (distance {distances[min_idx]:.1f} px)")
else:
    print("No white pixels found")

east_border = []
for x in range(475, min(img.shape[1], 700)):
    if mask[349, x]:
        east_border.append(x)
print(f"White pixels directly East: {east_border}")

west_border = []
for x in range(475, max(0, 300), -1):
    if mask[349, x]:
        west_border.append(x)
print(f"White pixels directly West: {west_border}")
