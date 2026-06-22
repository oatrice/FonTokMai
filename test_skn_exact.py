from app.services.tmd_radar_processor import TMDRadarProcessor

proc = TMDRadarProcessor("skn240")
lat, lng = 17.1607, 104.1486 # Exact center of skn240
px, py = proc.latlng_to_pixel(lat, lng, is_loop=False)
print(f"Center lat/lng (17.1607, 104.1486) -> px: {px}, py: {py}")

# Test a location slightly away
lat, lng = 17.97, 102.63 # Vientiane
px, py = proc.latlng_to_pixel(lat, lng, is_loop=False)
print(f"Vientiane lat/lng (17.97, 102.63) -> px: {px}, py: {py}")
