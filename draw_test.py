import cv2
img = cv2.imread("skn240_latest.jpg")
cv2.circle(img, (231, 188), radius=20, color=(0, 0, 255), thickness=-1)
cv2.circle(img, (693, 566), radius=20, color=(0, 255, 0), thickness=-1)
cv2.imwrite("test_skn.jpg", img)
