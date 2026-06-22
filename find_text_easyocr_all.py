import urllib.request
import cv2
import numpy as np
import easyocr

req = urllib.request.urlopen("https://weather.tmd.go.th/skn/skn240_latest.jpg")
arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
img = cv2.imdecode(arr, -1)

reader = easyocr.Reader(['en'])
results = reader.readtext(img)

for (bbox, text, prob) in results:
    if prob > 0.5:
        print(f"Text: '{text}'")
