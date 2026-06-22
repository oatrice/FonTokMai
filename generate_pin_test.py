import cv2
from app.services.tmd_radar_processor import TMDRadarProcessor

processor = TMDRadarProcessor("skn240")
img = cv2.imread("current_skn.jpg")
processor.draw_pin_on_frame(img, 475, 349)
cv2.imwrite("backend/tmp/test_475_349.png", img)
