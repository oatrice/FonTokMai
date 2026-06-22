from app.services.tmd_radar_processor import TMDRadarProcessor
proc = TMDRadarProcessor("skn240")
print("Loop Sakon:", proc.latlng_to_pixel(17.1607, 104.1486, is_loop=True))
print("Loop Savan:", proc.latlng_to_pixel(16.12, 105.73, is_loop=True))
