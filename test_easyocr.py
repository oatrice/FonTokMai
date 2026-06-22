import easyocr
import cv2
reader = easyocr.Reader(['en'])
img = cv2.imread("skn240_latest.jpg")
results = reader.readtext(img)
for res in results:
    bbox, text, conf = res
    print(f"{text}: {bbox}")
