from app.services.tmd_radar_processor import TMDRadarProcessor
processor = TMDRadarProcessor("skn240")
x1, y1 = processor.latlng_to_pixel(17.41, 104.78, is_loop=False)
x2, y2 = processor.latlng_to_pixel(17.4142, 104.3943, is_loop=False)
print(f"17.41, 104.78 -> {x1}, {y1}")
print(f"17.4142, 104.3943 -> {x2}, {y2}")
