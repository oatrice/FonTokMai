from app.services.tmd_radar_processor import TMDRadarProcessor

lat, lng = 17.4142, 104.3943
proc = TMDRadarProcessor("kkn240")
print(f"Home on kkn240 (Azimuthal): {proc.latlng_to_pixel(lat, lng, is_loop=False, projection='azimuthal')}")
print(f"Home on kkn240 (Linear): {proc.latlng_to_pixel(lat, lng, is_loop=False, projection='linear')}")
