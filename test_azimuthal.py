import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def bearing(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return math.atan2(y, x)

dist = haversine(6.9248, 100.4385, 6.626147, 101.103772)
brg = bearing(6.9248, 100.4385, 6.626147, 101.103772)

r_px = (dist / 240.0) * 360.0
dx = r_px * math.sin(brg)
dy = -r_px * math.cos(brg)

print(f"Azimuthal dx: {dx}, dy: {dy}")

print(f"User px: {360 + dx}, User py: {360 + dy}")

scaled_x = (360 + dx) * (1280.0 / 720.0)
scaled_y = (360 + dy) * (1280.0 / 720.0)
print(f"Scaled to 1280: x={scaled_x}, y={scaled_y}")
