import sys
from app.services.tmd_radar_processor import TMDRadarProcessor

processor = TMDRadarProcessor("skn240")
x, y = processor.latlng_to_pixel(17.4142, 104.3943, is_loop=False)
print(f"skn240: lat=17.4142, lng=104.3943 -> px={x}, py={y}")
