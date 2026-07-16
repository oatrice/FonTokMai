import cv2
import numpy as np

# Create a test image
img = np.zeros((300, 300, 3), dtype=np.uint8)

# Create some scattered points
pts1 = np.random.randint(50, 100, (30, 2))
pts2 = np.random.randint(200, 250, (20, 2))
pts3 = np.random.randint(50, 250, (10, 2)) # noise

pts = np.vstack((pts1, pts2, pts3))
pts = pts.reshape(-1, 1, 2)

x, y, w, h = cv2.boundingRect(pts)
margin = 5
mask_w, mask_h = w + 2 * margin, h + 2 * margin
mask = np.zeros((mask_h, mask_w), dtype=np.uint8)

local_pts = pts - np.array([[[x - margin, y - margin]]], dtype=np.int32)
for pt in local_pts:
    px, py = pt[0]
    if 0 <= px < mask_w and 0 <= py < mask_h:
        # draw circle to group nearby points
        cv2.circle(mask, (px, py), 15, 255, -1)

contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

img1 = img.copy()
cv2.polylines(img1, [c + np.array([[[x - margin, y - margin]]]) for c in contours], True, (0, 255, 0), 2)

img2 = img.copy()
hulls = [cv2.convexHull(c) for c in contours]
cv2.polylines(img2, [h + np.array([[[x - margin, y - margin]]]) for h in hulls], True, (0, 0, 255), 2)

for pt in pts:
    cv2.circle(img1, tuple(pt[0]), 2, (255, 255, 255), -1)
    cv2.circle(img2, tuple(pt[0]), 2, (255, 255, 255), -1)

cv2.imwrite("test_contour.png", img1)
cv2.imwrite("test_hull.png", img2)
print("Done")
