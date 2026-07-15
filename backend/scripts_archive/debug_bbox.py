import sys
sys.path.append("/Users/oatrice/Software-projects/FonMaYang/backend")
from app.services.tmd_radar_processor import TMDRadarProcessor

p = TMDRadarProcessor(station_code="kkn240")
cfg = p.config

print(f"BBox: lat {cfg.bbox.lat_min} to {cfg.bbox.lat_max}, lng {cfg.bbox.lng_min} to {cfg.bbox.lng_max}")
print(f"Image size: {cfg.loop_crop_width} x {cfg.loop_crop_height}")

lat_span = cfg.bbox.lat_max - cfg.bbox.lat_min
lng_span = cfg.bbox.lng_max - cfg.bbox.lng_min

lat_km = lat_span * 111.0
lng_km = lng_span * 111.0 * 0.866  # cos(lat)

km_per_px_x = lng_km / cfg.loop_crop_width
km_per_px_y = lat_km / cfg.loop_crop_height

print(f"\nLat span: {lat_span:.3f} deg = {lat_km:.1f} km")
print(f"Lng span: {lng_span:.3f} deg = {lng_km:.1f} km")
print(f"km/px X: {km_per_px_x:.3f}")
print(f"km/px Y: {km_per_px_y:.3f}")
print(f"Aspect ratio difference: {km_per_px_x / km_per_px_y:.2f}x")
print()

# Convert user-observed pixel velocity to km/h
user_vx_px = 30  # px per 15 min
user_vy_px = -10

user_vx_km = user_vx_px * km_per_px_x
user_vy_km = user_vy_px * km_per_px_y

print(f"User-observed cloud speed:")
print(f"  vx = {user_vx_px} px/15min = {user_vx_km:.1f} km/15min = {user_vx_km*4:.1f} km/h (East)")
print(f"  vy = {user_vy_px} px/15min = {user_vy_km:.1f} km/15min = {user_vy_km*4:.1f} km/h (North)")
import math
speed = math.sqrt(user_vx_km**2 + user_vy_km**2) * 4
print(f"  Total speed: {speed:.1f} km/h")

