from app.services.tmd_radar_processor import TMDRadarProcessor

processor = TMDRadarProcessor("skn240")
user_px, user_py = processor.latlng_to_pixel(17.3920, 104.7696, is_loop=False)
print(f"Nakhon Phanom pixels: {user_px}, {user_py}")
