import cv2
import numpy as np

roi1 = cv2.imread("backend/tmp/roi_475_349.png")
roi2 = cv2.imread("backend/tmp/roi_260_243.png")

def check_roi(name, roi):
    b, g, r = cv2.split(roi)
    white_mask = (b > 200) & (g > 200) & (r > 200)
    blue_mask = (b > 150) & (g < 100) & (r < 100)
    print(f"{name} -> White: {np.sum(white_mask)}, Blue: {np.sum(blue_mask)}")

check_roi("roi_475_349", roi1)
check_roi("roi_260_243", roi2)
