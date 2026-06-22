import asyncio
from datetime import datetime, timezone
from PIL import Image
import numpy as np

from app.services.tmd_radar_processor import TMDRadarProcessor

async def main():
    processor = TMDRadarProcessor("skn240")
    img = Image.open("current_skn.jpg").convert('RGB')
    curr_frame = np.array(img)
    
    lat = 17.41
    lng = 104.78
    user_px, user_py = processor.latlng_to_pixel(lat, lng, is_loop=False)
    
    tracking_bytes = processor.generate_radar_tracking_image(curr_frame.copy(), user_px, user_py, [])
    if tracking_bytes:
        with open("backend/tmp/test_np_tracking.png", "wb") as f:
            f.write(tracking_bytes)
            print("Generated tracking image for Nakhon Phanom!")

asyncio.run(main())
