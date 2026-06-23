from app.services.tmd_radar_processor import TMDRadarProcessor
from geopy.distance import geodesic

# 559 = 436 + px_dist_x => px_dist_x = 123
# 411 = 392 - px_dist_y => px_dist_y = -19
px_dist_x = 123
px_dist_y = -19
# distance_km * 1.516 * sin(bearing) = 123 => dist_sin = 81.1 km
# distance_km * 1.516 * cos(bearing) = -19 => dist_cos = -12.5 km
# distance_km = sqrt(81.1^2 + 12.5^2) = 82 km
import math
bearing = math.degrees(math.atan2(81.1, -12.5))
if bearing < 0: bearing += 360
origin = (17.1607, 104.1486)
dest = geodesic(kilometers=82).destination(origin, bearing)
print(f"Lat: {dest.latitude}, Lng: {dest.longitude}")
