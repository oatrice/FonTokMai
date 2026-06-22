from app.services.tmd_radar_processor import TMDRadarProcessor

processor = TMDRadarProcessor("skn240")
user_px, user_py = processor.latlng_to_pixel(17.4142, 102.3943, is_loop=False)
print(f"Pixels for 102.3943: {user_px}, {user_py}")
