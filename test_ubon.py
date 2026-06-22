from app.services.tmd_radar_processor import TMDRadarProcessor

lat, lng = 15.24, 104.85
proc = TMDRadarProcessor("skn240")
print(f"Ubon computed: {proc.latlng_to_pixel(lat, lng, is_loop=False)}")
