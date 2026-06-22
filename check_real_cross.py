import cv2
import numpy as np

img = cv2.imread("/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/.tempmediaStorage/media_758941b4-7979-4dd6-9917-012a34e7d6c0_1782122488765.jpg")

# The image is 800x800. Let's check 475, 349
roi1 = img[320:380, 440:500]
cv2.imwrite("backend/tmp/roi_475_349.png", roi1)

# Let's check 260, 243
roi2 = img[210:270, 230:290]
cv2.imwrite("backend/tmp/roi_260_243.png", roi2)
