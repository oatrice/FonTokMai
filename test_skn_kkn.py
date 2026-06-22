from app.services.tmd_radar_processor import TMDRadarProcessor

lat, lng = 16.43, 102.82
proc = TMDRadarProcessor("skn240")
print(f"Khon Kaen on skn240: {proc.latlng_to_pixel(lat, lng, is_loop=False)}")
