import urllib.request
import cv2
import numpy as np
import math

req = urllib.request.urlopen("https://weather.tmd.go.th/skn/skn240_latest.jpg")
arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
img = cv2.imdecode(arr, -1)

# Let's plot Sakon Nakhon (center) and something 100km away.
center_lat = 17.1607
center_lng = 104.1486
radius_km = 240.0
crop_width = 728
crop_height = 728
crop_x = 72
crop_y = 28

def latlng_to_px(lat, lng):
    R = 6371.0
    lat1 = math.radians(center_lat)
    lon1 = math.radians(center_lng)
    lat2 = math.radians(lat)
    lon2 = math.radians(lng)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_km = R * c
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.atan2(y, x)
    pixel_radius = crop_width / 2.0
    r_px = (distance_km / radius_km) * pixel_radius
    dx = r_px * math.sin(bearing)
    dy = -r_px * math.cos(bearing)
    px = int(crop_width / 2.0 + dx) + crop_x
    py = int(crop_height / 2.0 + dy) + crop_y
    return px, py

# 1. Sakon Nakhon city (should be center)
c_px, c_py = latlng_to_px(17.1607, 104.1486)
print(f"Center px: {c_px}, {c_py}")
cv2.circle(img, (c_px, c_py), 10, (0, 0, 255), -1)

# 2. Vientiane (Laos) ~ 17.9757, 102.6331
v_px, v_py = latlng_to_px(17.9757, 102.6331)
print(f"Vientiane px: {v_px}, {v_py}")
cv2.circle(img, (v_px, v_py), 10, (255, 0, 0), -1)

cv2.imwrite("test_skn.jpg", img)
