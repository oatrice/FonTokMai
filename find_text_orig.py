import cv2
import easyocr

reader = easyocr.Reader(['en', 'th'])
img = cv2.imread("current_skn.jpg")
results = reader.readtext(img)
for res in results:
    bbox, text, conf = res
    center_x = (bbox[0][0] + bbox[1][0]) / 2
    center_y = (bbox[0][1] + bbox[2][1]) / 2
    if 'kalasin' in text.lower() or 'nakhon phanom' in text.lower():
        print(f"TEXT: '{text}' at {center_x}, {center_y}")
