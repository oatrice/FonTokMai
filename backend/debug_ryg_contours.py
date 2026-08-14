import os
import httpx
import cv2
import numpy as np
from datetime import datetime, timezone

from app.services.tmd_radar.processor import TMDRadarProcessor
from app.services.tmd_radar_config import STATIONS

def run_debug_ryg():
    # 1. Download latest Rayong radar image
    url = "https://weather.tmd.go.th/ryg/ryg240_latest.jpg"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    
    img_path = "/tmp/ryg_latest.jpg"
    try:
        print(f"Downloading radar image from {url}...")
        resp = httpx.get(url, headers=headers, timeout=10.0)
        if resp.status_code == 200:
            with open(img_path, "wb") as f:
                f.write(resp.content)
            print("Download successful.")
    except Exception as e:
        print(f"Download failed: {e}. Attempting to use existing /tmp/ryg_latest.jpg")

    if not os.path.exists(img_path):
        print(f"Error: {img_path} not found!")
        return

    # 2. Read raw image and apply Rayong station crop
    raw_bgr = cv2.imread(img_path)
    st = STATIONS["ryg"]
    
    crop_x, crop_y, crop_w, crop_h = st.static_crop_x, st.static_crop_y, st.static_crop_width, st.static_crop_height
    print(f"Station ryg Crop Config: x={crop_x}, y={crop_y}, w={crop_w}, h={crop_h}")

    cropped_bgr = raw_bgr[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w].copy()
    cropped_rgb = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2RGB)
    
    processor = TMDRadarProcessor(station_code="ryg")
    user_x, user_y = crop_w // 2, crop_h // 2
    
    # 3. Detect rain clusters
    clusters = processor.get_all_rain_clusters(
        frame=cropped_rgb,
        flow=np.zeros((*cropped_rgb.shape[:2], 2), dtype=np.float32),
        user_x=user_x,
        user_y=user_y,
        scan_radius=None,
        min_dbz=10.0,
        cluster_dist=8,
        min_size=5
    )
    
    clouds = processor.find_approaching_clouds(
        cropped_rgb,
        cropped_rgb,
        np.zeros((*cropped_rgb.shape[:2], 2), dtype=np.float32),
        user_x,
        user_y,
        search_radius=200,
        min_dbz=10.0,
        cluster_dist=8,
        hit_radius=20,
        cluster_min=3
    )

    print(f"\n=== CLUSTER COORDINATE LOGS ({len(clusters)} clusters detected) ===")
    for i, c in enumerate(clusters):
        cx, cy = int(c["cx"]), int(c["cy"])
        min_x, min_y = c.get("min_x", cx), c.get("min_y", cy)
        max_x, max_y = c.get("max_x", cx), c.get("max_y", cy)
        dbz = c.get("dbz", 20.0)
        c["label"] = chr(ord('A') + min(i, 25))
        print(f"Cluster #{i+1} [{c['label']}]: Centroid=(X:{cx}, Y:{cy}) BBox=(X:{min_x}..{max_x}, Y:{min_y}..{max_y}) dBZ={dbz:.1f}")

    # 4. Render Tracking Image using FonMaYang Production Engine
    img_bytes = processor.generate_radar_tracking_image(
        frame=cropped_rgb,
        user_x=user_x,
        user_y=user_y,
        clouds=clouds,
        all_rain_clusters=clusters,
        time_utc=datetime.now(timezone.utc),
        cluster_dist_approaching=8,
        cluster_dist_ambient=8
    )

    out_path = "./ryg_radar_grid_overlay.png"
    with open(out_path, "wb") as f:
        f.write(img_bytes)

    print(f"\nSuccessfully generated output image at: {os.path.abspath(out_path)}")

if __name__ == "__main__":
    run_debug_ryg()
