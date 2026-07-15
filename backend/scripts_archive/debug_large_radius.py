import asyncio
import sys
import numpy as np

sys.path.append("/Users/oatrice/Software-projects/FonMaYang/backend")
from app.services.tmd_radar_processor import TMDRadarProcessor

async def main():
    processor = TMDRadarProcessor(station_code="kkn240")
    frames = await processor.fetch_loop_gif_and_extract_frames()
    
    lat = 17.839305
    lng = 102.573027
    px, py = processor.latlng_to_pixel(lat, lng, processor.config)
    
    flow = processor.calculate_optical_flow(frames)
    vx, vy = processor.get_flow_vector_at(flow, px, py)
    
    target_src_x = int(round(px - vx * 1))
    target_src_y = int(round(py - vy * 1))
    
    for i in range(len(frames)):
        idx = -(i + 1)
        track_x = int(round(target_src_x - i * vx))
        track_y = int(round(target_src_y - i * vy))
        
        # Test large radius
        d = processor._get_max_dbz_in_radius(frames[idx], track_x, track_y, radius=30)
        print(f"{i*15}m ago: Linear Track({track_x},{track_y}) Max DBZ in R=30 -> {d}")

if __name__ == "__main__":
    asyncio.run(main())
