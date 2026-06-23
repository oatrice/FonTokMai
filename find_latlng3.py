from app.services.tmd_radar_processor import TMDRadarProcessor
from geopy.distance import geodesic
import math

# We want to find the lat, lng for X=599, Y=373 in the static image
# processor = TMDRadarProcessor("skn240")
# center_x = 436, center_y = 392
# px_dist_x = X - center_x = 599 - 436 = 163
# px_dist_y = center_y - Y = 392 - 373 = 19
px_dist_x = 163
px_dist_y = 19
# pixels_per_km = 1.516
# distance_km * 1.516 * sin(bearing) = 163 => dist_sin = 107.5 km
# distance_km * 1.516 * cos(bearing) = 19 => dist_cos = 12.5 km
# distance_km = sqrt(107.5^2 + 12.5^2) = 108.2 km
bearing = math.degrees(math.atan2(107.5, 12.5))
if bearing < 0: bearing += 360
origin = (17.1607, 104.1486)
dest = geodesic(kilometers=108.2).destination(origin, bearing)
print(f"Lat: {dest.latitude}, Lng: {dest.longitude}")
