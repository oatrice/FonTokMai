import easyocr
import cv2
reader = easyocr.Reader(['en', 'th'])
img = cv2.imread("test_user_image.jpg")
results = reader.readtext(img)
for res in results:
    bbox, text, conf = res
    print(f"{text}: {bbox}")
