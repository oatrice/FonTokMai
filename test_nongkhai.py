from app.services.tmd_radar_processor import TMDRadarProcessor

lat, lng = 17.88, 102.74
proc = TMDRadarProcessor("skn240")
print(f"Nong Khai computed: {proc.latlng_to_pixel(lat, lng, is_loop=False)}")
