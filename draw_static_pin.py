import cv2
img = cv2.imread('test_static.jpg')
cv2.circle(img, (475, 349), radius=10, color=(0, 0, 255), thickness=-1)
cv2.imwrite('/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/test_static_pinned.jpg', img)
