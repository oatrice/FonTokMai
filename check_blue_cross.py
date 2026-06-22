import cv2
import numpy as np

img = cv2.imread("/Users/oatrice/.gemini/antigravity/brain/758941b4-7979-4dd6-9917-012a34e7d6c0/.tempmediaStorage/media_758941b4-7979-4dd6-9917-012a34e7d6c0_1782122488765.jpg")
roi = img[380:440, 530:590]
cv2.imwrite("backend/tmp/roi_cross.png", roi)
