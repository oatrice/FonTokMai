import asyncio
from app.services.weather_manager import fetch_latest_radar
from app.services.tmd_radar_processor import TMDRadarProcessor

async def main():
    processor = TMDRadarProcessor("skn240")
    curr_frame, prev_frame, now_utc, prev_utc = await fetch_latest_radar(processor)
    if curr_frame is None:
        return
        
    flow = processor.compute_optical_flow(prev_frame, curr_frame)
    clouds = processor.predict_approaching_clouds(curr_frame, prev_frame, flow, 537, 349)
    print("Found clouds:", len(clouds))
    for c in clouds:
        print(c)
        
asyncio.run(main())
