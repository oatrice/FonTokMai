import urllib.request
import cv2
import numpy as np
import pytesseract

req = urllib.request.urlopen("https://weather.tmd.go.th/skn/skn240_latest.jpg")
arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
img = cv2.imdecode(arr, -1)

d = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
for i in range(len(d['text'])):
    if 'Sakon' in d['text'][i] or 'Nakhon' in d['text'][i]:
        print(f"Found '{d['text'][i]}' at ({d['left'][i]}, {d['top'][i]})")
