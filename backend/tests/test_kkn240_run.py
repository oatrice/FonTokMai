import asyncio
import numpy as np
import cv2
import os
import sys

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.tmd_radar_processor import TMDRadarProcessor
from app.services.weather_manager import _DEV_CONFIG
from app.repositories.sqlite import SQLiteLocationRepository
from app.models import Base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

async def main():
    # 1. Setup SQLite in-memory database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with TestingSessionLocal() as session:
        repo = SQLiteLocationRepository(session)
        # Register user target location: 16.6944, 104.5306
        chat_id = "test_user_6346467495"
        await repo.save_location(chat_id, 16.6944, 104.5306, "FOREVER", name="default")

        # 2. Initialize TMDRadarProcessor and fetch frames like production
        # (weather_manager.py loop-GIF fallback path)
        processor = TMDRadarProcessor("skn240")

        print("Fetching loop GIF frames from TMD (production method)...")
        frames, last_modified_dt, loop_bytes = await processor.fetch_loop_gif_and_extract_frames()
        print(f"Extracted {len(frames)} frames (last_modified={last_modified_dt}).")

        if len(frames) < 2:
            print("ERROR: Fewer than 2 frames extracted from loop GIF. "
                  "Cannot compute optical flow. Aborting.")
            return

        # Keep only the last 6 frames and normalize shapes (weather_manager.py lines 628-632)
        frames = frames[-6:]
        target_shape = frames[-1].shape[:2]
        for i in range(len(frames) - 1):
            if frames[i].shape[:2] != target_shape:
                frames[i] = cv2.resize(frames[i], (target_shape[1], target_shape[0]), interpolation=cv2.INTER_NEAREST)
        print(f"Using last {len(frames)} frames, shape={target_shape}.")

        # 3. Compute optical flow like production
        flow_mode = _DEV_CONFIG.get("flow_mode", "latest")
        if flow_mode == "average":
            flow = processor.calculate_average_optical_flow(frames)
        else:
            flow = processor.calculate_optical_flow(frames)
        print(f"Optical flow computed (flow_mode={flow_mode}).")

        # 4. Find user pixel coordinates (is_loop=True: frames come from the loop GIF)
        user_x, user_y = processor.latlng_to_pixel(16.6944, 104.5306, is_loop=True)
        print(f"User location: 16.6944, 104.5306 -> Pixel coordinate (X={user_x}, Y={user_y})")

        # 5. Check all clusters - params identical to production (weather_manager.py line 728-735)
        clusters = processor.get_all_rain_clusters(
            frame=frames[-1],
            flow=flow,
            user_x=user_x,
            user_y=user_y,
            scan_radius=100,
            min_dbz=0.1,
            cluster_dist=25,
            min_size=5
        )

        print("\n=== CLUSTER ANALYSIS (OFFLINE SCRIPT) ===")
        for c in clusters:
            lbl = c['label']
            cx, cy = c['cx'], c['cy']
            pkx, pky = c.get('peak_cx', cx), c.get('peak_cy', cy)
            dist = c['dist']
            drift = np.hypot(pkx - cx, pky - cy)
            print(f"Cluster [{lbl}]: Centroid=({cx}, {cy}), Peak=({pkx}, {pky}), Drift={drift:.2f}px, Size={c['size']}, Dist={dist:.1f}px")

        # 6. Generate visual tracking image
        out_image_bytes = processor.generate_radar_tracking_image(
            frame=frames[-1],
            user_x=user_x,
            user_y=user_y,
            clouds=[],
            all_rain_clusters=clusters,
            locked_target_id=None
        )

        tests_dir = os.path.dirname(__file__)
        out_path = os.path.join(tests_dir, "test_tracking_out.png")
        with open(out_path, "wb") as f:
            f.write(out_image_bytes)
        print(f"\nSaved output visual image to: {os.path.abspath(out_path)}")

if __name__ == "__main__":
    asyncio.run(main())
