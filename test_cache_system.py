import asyncio
import logging
import sys
from dotenv import load_dotenv

# Load environment variables so it connects to Firestore
load_dotenv('backend/.env')

from backend.app.services.tmd_radar_processor import TMDRadarProcessor
from backend.app.dependencies import get_repo_context
from backend.app.scheduler_tasks import fetch_tmd_radar_routine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_cache_system():
    station = "kkn240"
    
    print("\n" + "="*50)
    print("🚀 PHASE 1: Run Cache Routine (Write to Firestore & Storage)")
    print("="*50)
    print("This will fetch from TMD and upload to Firebase Storage...")
    await fetch_tmd_radar_routine()
    
    print("\n" + "="*50)
    print("🚀 PHASE 2: Verify Firestore Database")
    print("="*50)
    async with get_repo_context() as repo:
        cache = await repo.get_latest_radar_cache(station)
        if cache:
            print(f"✅ Found Cache Metadata for {station}:")
            print(f"   - Static URL: {cache.get('static_url')}")
            print(f"   - Loop URL: {cache.get('loop_url')}")
            print(f"   - Timestamp: {cache.get('timestamp')}")
        else:
            print(f"❌ No cache found for {station}")
            return

    print("\n" + "="*50)
    print("🚀 PHASE 3: Read from Cache (Simulate Predictor)")
    print("="*50)
    processor = TMDRadarProcessor(station)
    
    print("-> Testing fetch_latest_image_bytes(use_cache=True)")
    static_bytes = await processor.fetch_latest_image_bytes(use_cache=True)
    if static_bytes:
        print(f"✅ Downloaded static image: {len(static_bytes)} bytes")
    else:
        print("❌ Failed to download static image")
        
    print("\n-> Testing fetch_loop_gif_and_extract_frames(use_cache=True)")
    frames, dt = await processor.fetch_loop_gif_and_extract_frames(use_cache=True)
    if frames:
        print(f"✅ Extracted {len(frames)} frames from Loop GIF")
        print(f"✅ Timestamp from cache: {dt}")
    else:
        print("❌ Failed to download loop gif")

if __name__ == "__main__":
    print("Running Cache System Test...")
    print("Make sure you are running this with: PYTHONPATH=backend .venv/bin/python test_cache_system.py")
    asyncio.run(test_cache_system())
