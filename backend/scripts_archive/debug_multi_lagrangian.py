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
    
    best_steps = 1
    target_src_x = int(round(px - vx * best_steps))
    target_src_y = int(round(py - vy * best_steps))
    
    for i in range(len(frames)):
        idx = -(i + 1)
        
        # Calculate theoretical track center
        track_x = int(round(target_src_x - i * vx))
        track_y = int(round(target_src_y - i * vy))
        
        max_d = 0
        best_tx = track_x
        best_ty = track_y
        
        radius = 5
        img = frames[idx]
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                sx = track_x + dx
                sy = track_y + dy
                if 0 <= sx < img.shape[1] and 0 <= sy < img.shape[0]:
                    d = processor.get_dbz_at_pixel(img, sx, sy)
                    if d > max_d:
                        max_d = d
                        best_tx = sx
                        best_ty = sy
                        
        print(f"{i*15}m ago (Frame {idx}): Track({track_x},{track_y}) -> MaxDBZ={max_d} at ({best_tx},{best_ty}). Offset: dx={best_tx-track_x}, dy={best_ty-track_y}")

if __name__ == "__main__":
    asyncio.run(main())
