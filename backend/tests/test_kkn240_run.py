import asyncio
import httpx
import numpy as np
import cv2
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.tmd_radar_processor import TMDRadarProcessor
from app.repositories.sqlite import SQLiteLocationRepository
from app.models import Base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

async def main():
    # 1. Download target GIF - Using the exact timestamp frame from the bot's logs (1784172600)
    # The URL pattern for GCS stored frames:
    url = "https://firebasestorage.googleapis.com/v0/b/fonmayang.firebasestorage.app/o/radar%2Fkkn240%2Fkkn240_1784174781.gif?alt=media&token=12b0611e-51fd-4866-830a-9cf5cef86753"
    tests_dir = os.path.dirname(__file__)
    gif_path = os.path.join(tests_dir, "test_kkn240_latest.gif")
    
    print(f"Downloading radar GIF from {url}...")
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        if r.status_code != 200:
            print(f"Failed to download specific timestamp. Falling back to latest...")
            url_fallback = "https://weather.tmd.go.th/kkn/kkn240_latest.gif"
            r = await client.get(url_fallback)
        with open(gif_path, "wb") as f:
            f.write(r.content)
    print("GIF downloaded.")

    # 2. Setup SQLite database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    TestingSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    async with TestingSessionLocal() as session:
        repo = SQLiteLocationRepository(session)
        chat_id = "test_user_6346467495"
        await repo.save_location(chat_id, 17.5139, 101.639, "FOREVER", name="default")
        
        processor = TMDRadarProcessor("kkn240")
        
        cap = cv2.VideoCapture(gif_path)
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        cap.release()
            
        print(f"Extracted {len(frames)} frames.")
        if len(frames) == 1:
            frames.append(frames[0])
        
        user_x, user_y = processor.latlng_to_pixel(17.5139, 101.639)
        print(f"User location: 17.5139, 101.639 -> Pixel coordinate (X={user_x}, Y={user_y})")
        
        prev_gray = cv2.cvtColor(frames[-2], cv2.COLOR_RGB2GRAY)
        curr_gray = cv2.cvtColor(frames[-1], cv2.COLOR_RGB2GRAY)
        flow = cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        
        clusters = processor.get_all_rain_clusters(
            frame=frames[-1],
            flow=flow,
            user_x=user_x,
            user_y=user_y,
            scan_radius=200,
            cluster_dist=15
        )
        
        print("\n=== CLUSTER ANALYSIS (OFFLINE SCRIPT) ===")
        for c in clusters:
            lbl = c['label']
            cx, cy = c['cx'], c['cy']
            pkx, pky = c.get('peak_cx', cx), c.get('peak_cy', cy)
            dist = c['dist']
            drift = np.hypot(pkx - cx, pky - cy)
            print(f"Cluster [{lbl}]: Centroid=({cx}, {cy}), Peak=({pkx}, {pky}), Drift={drift:.2f}px, Size={c['size']}, Dist={dist:.1f}px")

        # Visual tracking image
        out_image_bytes = processor.generate_radar_tracking_image(
            frame=frames[-1],
            user_x=user_x,
            user_y=user_y,
            clouds=[],
            all_rain_clusters=clusters,
            locked_target_id=None
        )
        
        out_path = os.path.join(tests_dir, "test_tracking_out.png")
        with open(out_path, "wb") as f:
            f.write(out_image_bytes)
        print(f"\nSaved output visual image to: {os.path.abspath(out_path)}")

if __name__ == "__main__":
    asyncio.run(main())
