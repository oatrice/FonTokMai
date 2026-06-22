from app.services.tmd_radar_processor import TMDRadarProcessor
import math

proc = TMDRadarProcessor("skn240")
# Center is 436, 392.
# 559, 411 -> dx = 123, dy = 19
# bearing: dx = r * sin(theta), dy = -r * cos(theta)
dx = 559 - 436
dy = 411 - 392
r_px = math.sqrt(dx**2 + dy**2)
bearing = math.atan2(dx, -dy)

dist_km = r_px / 364 * 240
print(f"Distance: {dist_km} km")

R = 6371.0
lat1 = math.radians(17.1607)
lon1 = math.radians(104.1486)
lat2 = math.asin(math.sin(lat1) * math.cos(dist_km/R) + math.cos(lat1) * math.sin(dist_km/R) * math.cos(bearing))
lon2 = lon1 + math.atan2(math.sin(bearing) * math.sin(dist_km/R) * math.cos(lat1), math.cos(dist_km/R) - math.sin(lat1) * math.sin(lat2))
print(f"Lat: {math.degrees(lat2)}, Lng: {math.degrees(lon2)}")

