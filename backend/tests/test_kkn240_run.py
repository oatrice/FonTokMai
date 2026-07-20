import asyncio
import math
import logging
from datetime import datetime, timezone
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

_FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "test_kkn240_frames.npz")


def _load_fixture() -> tuple:
    """Load frames, flow, flow_mode, and metadata from .npz fixture.

    Returns (frames, flow, flow_mode, metadata_dict) or (None,)*4 if missing.
    metadata_dict contains keys: last_modified_dt, frame_timestamps, station
    """
    if not os.path.exists(_FIXTURE_PATH):
        return None, None, None, None

    data = np.load(_FIXTURE_PATH, allow_pickle=True)
    frame_arr = data["frames"]
    frames = [np.array(frame_arr[i]) for i in range(frame_arr.shape[0])]
    flow = np.array(data["flow"])
    flow_mode = str(data.get("flow_mode", "average"))
    if isinstance(flow_mode, bytes):
        flow_mode = flow_mode.decode()

    meta = dict(data.get("meta", {}).item()) if "meta" in data else {}

    print(f"Loaded fixture ({len(frames)} frames, flow={flow.shape}, mode={flow_mode})")
    return frames, flow, flow_mode, meta


def _save_fixture(frames: list, flow: np.ndarray, flow_mode: str,
                  last_modified_dt, frame_timestamps: list,
                  frame_urls: list = None) -> None:
    """Save frames, flow, and metadata to .npz fixture.

    Frames are stacked into a single 4D array (N, H, W, C) for efficient storage.
    frame_urls are optionally saved for reproducibility from production [FRAME_ID] logs.
    """
    frame_arr = np.stack(frames, axis=0)  # (N, H, W, 3)
    meta = {
        "last_modified_dt": str(last_modified_dt) if last_modified_dt else "",
        "frame_timestamps": frame_timestamps,
        "frame_urls": frame_urls or [],
        "station": "skn240",
    }
    np.savez_compressed(
        _FIXTURE_PATH,
        frames=frame_arr,
        flow=flow,
        flow_mode=flow_mode,
        meta=meta,
    )
    print(f"Saved fixture to: {_FIXTURE_PATH}")


async def _download_frames_from_urls(frame_urls: list, last_modified_dt=None) -> tuple:
    """Download frames from Firebase Storage URLs and reconstruct frame data.

    Returns (frames, last_modified_dt, frame_timestamps, frame_urls_out) or (None,)*4 on failure.
    Uses the same approach as weather_manager.load_persistent_cache_to_memory.
    """
    if not frame_urls:
        return None, None, None, None

    import numpy as np
    from google.cloud import storage

    bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "fonmayang.firebasestorage.app")
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    async def _fetch_blob(url):
        blob = bucket.blob(url)
        try:
            img_bytes = await asyncio.to_thread(blob.download_as_bytes)
            return img_bytes
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            return None

    # Download all frames in parallel
    results = await asyncio.gather(*[_fetch_blob(url) for url in frame_urls])
    valid = [(b, int(url.split("_")[-1].split(".")[0]) if "_" in url else 0)
             for b, url in zip(results, frame_urls) if b is not None]

    if len(valid) < 2:
        print("ERROR: Fewer than 2 frames could be downloaded from URLs.")
        return None, None, None, None

    valid.sort(key=lambda x: x[1])

    # Decode frames
    frames = []
    target_shape = None
    for f_bytes, ts in valid[-6:]:
        t_np = np.frombuffer(f_bytes, np.uint8)
        frame = cv2.imdecode(t_np, cv2.IMREAD_COLOR)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if target_shape is None:
            target_shape = frame.shape[:2]
        elif frame.shape[:2] != target_shape:
            frame = cv2.resize(frame, (target_shape[1], target_shape[0]), interpolation=cv2.INTER_NEAREST)
        frames.append(frame)

    frame_timestamps = [ts for _, ts in valid[-6:]]
    if not last_modified_dt:
        last_modified_dt = datetime.fromtimestamp(frame_timestamps[-1], tz=timezone.utc)

    print(f"Downloaded {len(frames)} frames from {len(frame_urls)} URL(s).")
    return frames, last_modified_dt, frame_timestamps, frame_urls

async def _fetch_from_backup_and_save_fixture(processor) -> tuple:
    """List and download the latest 6 frames from GCS radar/skn240_backup/ and save as fixture."""
    bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "fonmayang.firebasestorage.app")
    from google.cloud import storage
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    print("Listing blobs in radar/skn240_backup/...")
    try:
        blobs = list(bucket.list_blobs(prefix="radar/skn240_backup/"))
        backup_frames = []
        for b in blobs:
            base_name = b.name.split("/")[-1]
            ts_str = base_name.replace("skn240_", "").replace(".gif", "")
            try:
                ts = int(ts_str)
                backup_frames.append({"url": b.name, "timestamp": ts})
            except ValueError:
                continue

        if not backup_frames:
            print("ERROR: No files found in radar/skn240_backup/")
            return None, None, None, None

        # Sort and take latest 6
        backup_frames = sorted(backup_frames, key=lambda x: x["timestamp"])[-6:]
        urls = [f["url"] for f in backup_frames]

        print(f"Downloading latest {len(urls)} frames from backup...")
        frames, last_modified_dt, frame_timestamps, frame_urls = await _download_frames_from_urls(urls)

        if frames:
            flow_mode = _DEV_CONFIG.get("flow_mode", "latest")
            if flow_mode == "average":
                flow = processor.calculate_average_optical_flow(frames)
            else:
                flow = processor.calculate_optical_flow(frames)
            _save_fixture(frames, flow, flow_mode, last_modified_dt, frame_timestamps, frame_urls=frame_urls)
            print("✅ Fixture successfully updated from backup!")
            meta = {
                "frame_timestamps": frame_timestamps,
                "frame_urls": frame_urls,
                "last_modified_dt": str(last_modified_dt)
            }
            return frames, flow, flow_mode, meta
    except Exception as e:
        print(f"Error loading from backup: {e}")
    return None, None, None, None


async def main():
    # 0. Make [TRACKING_IMG] info logs from tracking.py visible
    logging.basicConfig(level=logging.INFO)

    # 1. Setup SQLite in-memory database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with TestingSessionLocal() as session:
        repo = SQLiteLocationRepository(session)
        # Register user target location: 17.1712, 104.4594
        chat_id = "test_user_6346467495"
        await repo.save_location(chat_id, 17.1712, 104.4594, "FOREVER", name="default")

        # 2. Initialize TMDRadarProcessor and fetch frames
        processor = TMDRadarProcessor("skn240")

        # 2a. Check if we want to force update from backup, or if fixture is missing
        force_update = os.getenv("UPDATE_FIXTURE", "false").lower() == "true"
        frames, flow, flow_mode, meta = None, None, None, None

        if not force_update:
            frames, flow, flow_mode, meta = _load_fixture()

        using_fixture = frames is not None

        if using_fixture:
            fixture_frame_timestamps = meta.get("frame_timestamps", [])
            fixture_frame_urls = meta.get("frame_urls", [])
            print(f"Replaying from fixture ({len(frames)} frames, {len(fixture_frame_urls)} URLs).")
        else:
            print("Fixture missing or UPDATE_FIXTURE=true. Attempting to fetch from GCS backup...")
            frames, flow, flow_mode, meta = await _fetch_from_backup_and_save_fixture(processor)
            if frames is not None:
                using_fixture = True
                fixture_frame_timestamps = meta.get("frame_timestamps", [])
                fixture_frame_urls = meta.get("frame_urls", [])
            else:
                # Try downloading from saved URLs first (if provided via env or from a prior [FRAME_ID] log)
                # Set TEST_FRAME_URLS env var to a comma-separated list of Firebase Storage URLs
                env_urls = os.getenv("TEST_FRAME_URLS", "")
                if env_urls:
                    url_list = [u.strip() for u in env_urls.split(",") if u.strip()]
                    print(f"Attempting to download {len(url_list)} frames from URLs...")
                    frames, last_modified_dt, fixture_frame_timestamps, frame_urls = (
                        await _download_frames_from_urls(url_list))
                    if frames is not None:
                        print(f"Downloaded {len(frames)} frames from URLs.")
                        _save_fixture(frames, None, None, last_modified_dt,
                                      fixture_frame_timestamps, frame_urls=frame_urls)
                        # Recompute flow after saving fixture
                        flow_mode = _DEV_CONFIG.get("flow_mode", "latest")
                        if flow_mode == "average":
                            flow = processor.calculate_average_optical_flow(frames)
                        else:
                            flow = processor.calculate_optical_flow(frames)
                        print(f"Optical flow computed (flow_mode={flow_mode}).")
                        frames, flow, flow_mode, meta = _load_fixture()
                        using_fixture = True
                        fixture_frame_urls = meta.get("frame_urls", [])
                        print(f"Replaying from URL-downloaded fixture ({len(frames)} frames).")
                    else:
                        print("URL download failed, falling back to loop GIF...")
                        env_urls = ""  # Reset to fall through to loop GIF

                if not env_urls:
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
                            frames[i] = cv2.resize(frames[i], (target_shape[1], target_shape[0]),
                                                   interpolation=cv2.INTER_NEAREST)
                    print(f"Using last {len(frames)} frames, shape={target_shape}.")

                    # Compute optical flow like production
                    flow_mode = _DEV_CONFIG.get("flow_mode", "latest")
                    if flow_mode == "average":
                        flow = processor.calculate_average_optical_flow(frames)
                    else:
                        flow = processor.calculate_optical_flow(frames)
                    print(f"Optical flow computed (flow_mode={flow_mode}).")

                    # Generate frame timestamps like production (weather_manager.py lines 634-639)
                    fixture_frame_timestamps = []
                    if last_modified_dt:
                        latest_ts = int(last_modified_dt.timestamp())
                        fixture_frame_timestamps = [
                            latest_ts - (len(frames) - 1 - i) * 900
                            for i in range(len(frames))
                        ]

                    # No Firebase URLs for loop GIF path
                    frame_urls = []
                    # Save to fixture for deterministic replay
                    _save_fixture(frames, flow, flow_mode, last_modified_dt,
                                  fixture_frame_timestamps, frame_urls=frame_urls)
                    fixture_frame_urls = []

        # Retrieve frame_urls from fixture metadata (may be empty for test-generated fixtures)
        fixture_frame_urls = meta.get("frame_urls", []) if using_fixture else []

        # Print frame identity like production [FRAME_ID] log
        print(
            f"[FRAME_ID] station=skn240, source={'fixture' if using_fixture else 'loop_gif'}, "
            f"n_frames={len(frames)} (last_ts={fixture_frame_timestamps[-1] if fixture_frame_timestamps else '?'}), "
            f"timestamps={fixture_frame_timestamps}, shape={frames[-1].shape[:2]}, "
            f"urls={fixture_frame_urls}"
        )

        # 4. Find user pixel coordinates (is_loop=True: frames come from the loop GIF)
        user_x, user_y = processor.latlng_to_pixel(17.1712, 104.4594, is_loop=True)
        print(f"User location: 17.1712, 104.4594 -> Pixel coordinate (X={user_x}, Y={user_y})")

        # 5a. Find approaching clouds - identical to production (weather_manager.py lines 689-726)
        curr_frame = frames[-1].copy()
        prev_frame = frames[-2].copy()
        _DEV_CONFIG["verbose"] = True
        _cfg = _DEV_CONFIG.copy()
        clouds = processor.find_approaching_clouds(
            curr_frame, prev_frame, flow, user_x, user_y,
            search_radius=_cfg.get("search_radius", 80),
            min_dbz=_cfg.get("min_dbz", 10.0),
            cluster_dist=20,
            hit_radius=_cfg.get("hit_radius", 20),
            cluster_min=_cfg.get("cluster_min", 3),
            dot_threshold=_cfg.get("dot_threshold", 0.5),
        )
        print(f"find_approaching_clouds returned {len(clouds)} cloud(s).")

        # 5b. Check all clusters - params identical to production (weather_manager.py line 785-791)
        clusters = processor.get_all_rain_clusters(
            frame=frames[-1],
            flow=flow,
            user_x=user_x,
            user_y=user_y,
            scan_radius=min(200, _cfg.get("search_radius", 80) + 20),
            min_dbz=0.1,  # Keep lower threshold for light rain
            cluster_dist=12,  # Reduced from 25 to 12 to split separate groups
            min_size=5
        )

        # 5c. Label all_rain_clusters FIRST (weather_manager.py lines 737-741)
        if clusters:
            for i, c in enumerate(clusters):
                # Use A-Z, then AA-ZZ if needed (though usually < 26)
                c["label"] = chr(ord('A') + min(i, 25))

        # 5d. Match labels from all_rain_clusters to clouds (weather_manager.py lines 743-776)
        if clusters and clouds:
            unique_clouds = {}
            for appr_c in clouds:
                matched_label = "?"
                min_d = 9999
                matched_amb = None
                for amb_c in clusters:
                    d = math.hypot(appr_c["cx"] - amb_c["cx"], appr_c["cy"] - amb_c["cy"])
                    if d < 150 and d < min_d:
                        min_d = d
                        matched_label = amb_c.get("label", "?")
                        matched_amb = amb_c

                appr_c["label"] = matched_label
                if matched_amb:
                    appr_c["cx"] = matched_amb["cx"]
                    appr_c["cy"] = matched_amb["cy"]
                    if "peak_cx" in matched_amb:
                        appr_c["peak_cx"] = matched_amb["peak_cx"]
                    if "peak_cy" in matched_amb:
                        appr_c["peak_cy"] = matched_amb["peak_cy"]
                    if "pixels" in matched_amb:
                        appr_c["pixels"] = matched_amb["pixels"]

                # Deduplicate: keep the one with smaller absolute eta (closer to impact or current)
                label = appr_c["label"]
                if label not in unique_clouds:
                    unique_clouds[label] = appr_c
                else:
                    existing = unique_clouds[label]
                    if abs(appr_c.get("eta_min", 9999)) < abs(existing.get("eta_min", 9999)):
                        unique_clouds[label] = appr_c
            clouds = list(unique_clouds.values())

        print("\n=== CLUSTER ANALYSIS (OFFLINE SCRIPT) ===")
        for c in clusters:
            lbl = c['label']
            cx, cy = c['cx'], c['cy']
            pkx, pky = c.get('peak_cx', cx), c.get('peak_cy', cy)
            dist = c['dist']
            drift = np.hypot(pkx - cx, pky - cy)
            print(f"Cluster [{lbl}]: Centroid=({cx}, {cy}), Peak=({pkx}, {pky}), Drift={drift:.2f}px, Size={c['size']}, Dist={dist:.1f}px")

        print("\n=== APPROACHING CLOUDS ===")
        if not clouds:
            print("(none)")
        for c in clouds:
            print(
                f"Cloud [{c.get('label', '?')}]: Centroid=({c.get('cx')}, {c.get('cy')}), "
                f"ETA={c.get('eta_min')}min, PredictedDBZ={c.get('predicted_dbz')}, "
                f"Approaching={c.get('approaching')}, Pixels={len(c.get('pixels', []))}"
            )

        # 6. Generate visual tracking image
        out_image_bytes = processor.generate_radar_tracking_image(
            frame=frames[-1],
            user_x=user_x,
            user_y=user_y,
            clouds=clouds,
            all_rain_clusters=clusters,
            time_utc=datetime.fromtimestamp(1784219585, timezone.utc),
            locked_target_id=None
        )

        tests_dir = os.path.dirname(__file__)
        out_path = os.path.join(tests_dir, "test_tracking_out.png")
        with open(out_path, "wb") as f:
            f.write(out_image_bytes)
        print(f"\nSaved output visual image to: {os.path.abspath(out_path)}")

if __name__ == "__main__":
    asyncio.run(main())
