import cv2
import easyocr
reader = easyocr.Reader(['en', 'th'])
img = cv2.imread("test_home.jpg")
results = reader.readtext(img)
for res in results:
    bbox, text, conf = res
    center_x = (bbox[0][0] + bbox[1][0]) / 2
    if center_x < 640:
        print(f"LEFT: {text} at {center_x}")
