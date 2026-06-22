import math

# Khon Kaen center
lat1 = math.radians(16.4385)
lon1 = math.radians(102.8272)
radius_km = 240.0
crop_width = 728.0

# Sakon Nakhon
lat = 17.1607
lng = 104.1486
lat2 = math.radians(lat)
lon2 = math.radians(lng)

dlon = lon2 - lon1
dlat = lat2 - lat1
a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
R = 6371.0
distance_km = R * c

y = math.sin(dlon) * math.cos(lat2)
x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
bearing = math.atan2(y, x)

r_px = (distance_km / radius_km) * (crop_width / 2.0)
dx = r_px * math.sin(bearing)
dy = -r_px * math.cos(bearing)

print(f"Distance: {distance_km} km")
print(f"dx: {dx}, dy: {dy}")
print(f"px: {int(72 + 364 + dx)}, py: {int(28 + 364 + dy)}")

