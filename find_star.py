import cv2
import numpy as np

img = cv2.imread("test_home.jpg")

# Search around 760, 558 for anything that stands out
roi = img[500:600, 700:800]
cv2.imwrite("backend/tmp/roi.png", roi)
