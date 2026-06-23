from app.services.tmd_radar_processor import TMDRadarProcessor
import math

processor = TMDRadarProcessor("skn240")
# We want to find lat, lng such that latlng_to_pixel(lat, lng, is_loop=True) == (466, 334)
# Reverse engineering latlng_to_pixel:
# pixel_x = int(center_x + px_dist_x) + offset_x
# pixel_y = int(center_y - px_dist_y) + offset_y
# 466 = 310 + px_dist_x + 61 => px_dist_x = 95
# 334 = 310 - px_dist_y + 24 => px_dist_y = 0
px_dist_x = 95
px_dist_y = 0
# distance_km * (310/240) * sin(bearing) = 95
# distance_km * (310/240) * cos(bearing) = 0
# So bearing is 90 degrees (East).
# distance_km = 95 / (310/240) = 73.5 km
# We need a point 73.5 km East of Sakon Nakhon (17.1607, 104.1486)
from geopy.distance import geodesic
origin = (17.1607, 104.1486)
dest = geodesic(kilometers=73.5).destination(origin, 90)
print(f"Lat: {dest.latitude}, Lng: {dest.longitude}")
