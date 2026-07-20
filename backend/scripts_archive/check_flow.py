import asyncio
import sys
sys.path.append("/Users/oatrice/Software-projects/FonMaYang/backend")
from app.services.tmd_radar_processor import TMDRadarProcessor

async def main():
    processor = TMDRadarProcessor(station_code="kkn240")
    frames = await processor.fetch_loop_gif_and_extract_frames()
    flow = processor.calculate_optical_flow(frames)
    
    lat = 17.839305
    lng = 102.573027
    px, py = processor.latlng_to_pixel(lat, lng, processor.config)
    
    vx, vy = processor.get_flow_vector_at(flow, px, py)
    print(f"User px: {px}, py: {py}")
    print(f"Flow at User vx: {vx}, vy: {vy}")
    
    # Let's find the max rain pixel
    max_d = 0
    best_steps = 1
    target_src_x = int(round(px - vx * best_steps))
    target_src_y = int(round(py - vy * best_steps))
    print(f"Target src (step {best_steps}) x: {target_src_x}, y: {target_src_y}")
    
    for i in range(6):
        tx = int(round(target_src_x - i * vx))
        ty = int(round(target_src_y - i * vy))
        if i < len(frames):
            d = processor.get_dbz_at_pixel(frames[-(i+1)], tx, ty)
            print(f"{i*15} mins ago, cloud was at {tx},{ty} with dbz: {d}")

if __name__ == "__main__":
    asyncio.run(main())
