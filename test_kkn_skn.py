from app.services.tmd_radar_processor import TMDRadarProcessor

lat, lng = 16.12, 105.73
proc_kkn = TMDRadarProcessor("kkn240")
print(f"kkn240 px: {proc_kkn.latlng_to_pixel(lat, lng, is_loop=False)}")
