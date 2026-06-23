import cv2
img = cv2.imread('test_frame0.png')
cv2.circle(img, (404, 297), radius=10, color=(0, 0, 255), thickness=-1)
cv2.imwrite('/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/test_frame0_pinned.png', img)
