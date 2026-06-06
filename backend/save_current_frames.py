import asyncio
import pickle
import sys

sys.path.append("/Users/oatrice/Software-projects/FonMaYang/backend")
from app.services.tmd_radar_processor import TMDRadarProcessor

async def main():
    processor = TMDRadarProcessor(station_code="kkn240")
    frames = await processor.fetch_loop_gif_and_extract_frames()
    
    import pickle
    out = "/Users/oatrice/Software-projects/FonMaYang/backend/tmp/saved_frames_kkn240.pkl"
    with open(out, "wb") as f:
        pickle.dump(frames, f)
    print(f"Saved {len(frames)} frames to {out}")
    print(f"Shape: {frames[0].shape}")

asyncio.run(main())
