from app.services.tmd_radar_processor import TMDRadarProcessor
import math

processor = TMDRadarProcessor("skn240")
center_x = 436
center_y = 392

# km per pixel
km_per_pixel_x = processor.config.km_per_pixel_x
km_per_pixel_y = processor.config.km_per_pixel_y

x = 78.75
y = 286.25

dx_km = (x - center_x) * km_per_pixel_x
dy_km = (center_y - y) * km_per_pixel_y

dist_km = math.sqrt(dx_km**2 + dy_km**2)
bearing = math.atan2(dx_km, dy_km)

R = 6371.0
center_lat = math.radians(processor.config.bbox.center_lat)
center_lng = math.radians(processor.config.bbox.center_lng)
angular_dist = dist_km / R

lat = math.asin(math.sin(center_lat) * math.cos(angular_dist) +
                math.cos(center_lat) * math.sin(angular_dist) * math.cos(bearing))

lng = center_lng + math.atan2(math.sin(bearing) * math.sin(angular_dist) * math.cos(center_lat),
                              math.cos(angular_dist) - math.sin(center_lat) * math.sin(lat))

print(f"Lat: {math.degrees(lat)}, Lng: {math.degrees(lng)}")
