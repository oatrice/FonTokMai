import asyncio
import sys
sys.path.append("/Users/oatrice/Software-projects/FonMaYang/backend")
from app.services.tmd_radar_processor import TMDRadarProcessor

async def main():
    processor = TMDRadarProcessor(station_code="kkn240")
    frames = await processor.fetch_loop_gif_and_extract_frames()
    
    lat = 17.839305
    lng = 102.573027
    px, py = processor.latlng_to_pixel(lat, lng, processor.config)
    
    flow_0m = processor.calculate_optical_flow(frames)
    vx, vy = processor.get_flow_vector_at(flow_0m, px, py)
    
    curr_x = int(round(px - vx))
    curr_y = int(round(py - vy))
    
    path = [(curr_x, curr_y)]
    
    for i in range(1, len(frames)):
        # Calculate flow from -(i+1) to -(i) using the processor's own method on a 2-frame slice
        sub_frames = [frames[-(i+1)], frames[-i]]
        flow = processor.calculate_optical_flow(sub_frames)
        f_vx, f_vy = processor.get_flow_vector_at(flow, curr_x, curr_y)
        
        curr_x = int(round(curr_x - f_vx))
        curr_y = int(round(curr_y - f_vy))
        path.append((curr_x, curr_y))
        
    for i, (tx, ty) in enumerate(path):
        d = processor._get_max_dbz_in_radius(frames[-(i+1)], tx, ty, radius=5)
        print(f"{i*15}m ago: Track({tx},{ty}) DBZ={d}")

if __name__ == "__main__":
    asyncio.run(main())
