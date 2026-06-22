import cv2
import numpy as np

# Read the template (full 800x800 map) and the screenshot
# We need to find where the 800x800 map is located inside the 1280x1280 screenshot.
# Wait, maybe the screenshot is SCALED!
# Let's just find the text "Sakon Nakhon" in the screenshot.
import easyocr
reader = easyocr.Reader(['en'])
img = cv2.imread("test_home.jpg")
results = reader.readtext(img)
for res in results:
    bbox, text, conf = res
    if "Sakon" in text or "Nakhon" in text or "Maha" in text or "Mukdahan" in text or "Kalasin" in text:
        print(f"{text}: {bbox}")

