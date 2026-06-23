import cv2
import urllib.request
import numpy as np
from app.services.tmd_radar_processor import TMDRadarProcessor

url = "https://weather.tmd.go.th/skn/skn240_latest.jpg"
req = urllib.request.urlopen(url)
arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
img = cv2.imdecode(arr, -1)

processor = TMDRadarProcessor("skn240")
# center
cx, cy = processor.latlng_to_pixel(17.1607, 104.1486, is_loop=False)
cv2.drawMarker(img, (cx, cy), (255, 0, 0), cv2.MARKER_CROSS, 20, 2)

# home
hx, hy = processor.latlng_to_pixel(17.4142, 104.3943, is_loop=False)
cv2.drawMarker(img, (hx, hy), (0, 255, 0), cv2.MARKER_CROSS, 20, 2)

cv2.imwrite("test_pin.jpg", img)
print(f"Center pin at: {cx}, {cy}")
print(f"Home pin at: {hx}, {hy}")
