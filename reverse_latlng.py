import math
from app.services.tmd_radar_config import STATIONS

def pixel_to_latlng(px, py, station_code):
    conf = STATIONS[station_code]
    center_lat = math.radians(conf.center_lat)
    center_lng = math.radians(conf.center_lng)
    
    center_x, center_y = 436, 392
    
    dx = px - center_x
    dy = py - center_y
    
    r_px = math.sqrt(dx**2 + dy**2)
    distance_km = (r_px / 364) * conf.radius_km
    
    c = distance_km / 6371.0
    
    bearing = math.atan2(dx, -dy)
    
    lat = math.asin(math.sin(center_lat)*math.cos(c) + math.cos(center_lat)*math.sin(c)*math.cos(bearing))
    lon = center_lng + math.atan2(math.sin(bearing)*math.sin(c)*math.cos(center_lat), math.cos(c)-math.sin(center_lat)*math.sin(lat))
    
    return math.degrees(lat), math.degrees(lon)

print(pixel_to_latlng(693, 566, "skn240"))
