import cv2, numpy as np
img = cv2.imread('/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/frame0.png')
cv2.circle(img, (406, 299), 5, (0, 0, 255), -1)
cv2.imwrite('/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/marked_loop2.jpg', img)
