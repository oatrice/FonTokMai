import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.tmd_radar_processor import TMDRadarProcessor

processor = TMDRadarProcessor("skn240")
loop_px = processor.latlng_to_pixel(17.4142, 104.3943, is_loop=True)
static_px = processor.latlng_to_pixel(17.4142, 104.3943, is_loop=False)

print(f"Loop Pixel: {loop_px}")
print(f"Static Pixel: {static_px}")

