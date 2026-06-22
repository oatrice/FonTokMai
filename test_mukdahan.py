from app.services.tmd_radar_processor import TMDRadarProcessor

lat, lng = 16.54, 104.71
proc = TMDRadarProcessor("skn240")
print(f"Mukdahan computed: {proc.latlng_to_pixel(lat, lng, is_loop=False)}")
