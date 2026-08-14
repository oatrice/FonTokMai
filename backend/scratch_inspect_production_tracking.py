import os
import httpx
import numpy as np
import cv2
from datetime import datetime, timezone

from app.services.tmd_radar.processor import TMDRadarProcessor
from app.services.tmd_radar_config import STATIONS

def test_production_tracking_image():
    url = "https://weather.tmd.go.th/ryg/ryg240_latest.jpg"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    
    try:
        resp = httpx.get(url, headers=headers, timeout=10.0)
        if resp.status_code == 200:
            with open("/tmp/ryg_latest.jpg", "wb") as f:
                f.write(resp.content)
    except Exception as e:
        print(f"Download warning: {e}")

    raw_bgr = cv2.imread("/tmp/ryg_latest.jpg")
    st = STATIONS["ryg"]
    
    crop_x, crop_y, crop_w, crop_h = st.static_crop_x, st.static_crop_y, st.static_crop_width, st.static_crop_height
    cropped_bgr = raw_bgr[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w].copy()
    cropped_rgb = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2RGB)
    
    processor = TMDRadarProcessor(station_code="ryg")
    user_x, user_y = crop_w // 2, crop_h // 2
    
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

    print("=== CLUSTER & CONTOUR COORDINATE LOGS ===")
    for i, c in enumerate(clusters):
        cx, cy = int(c["cx"]), int(c["cy"])
        min_x, min_y = c.get("min_x", cx), c.get("min_y", cy)
        max_x, max_y = c.get("max_x", cx), c.get("max_y", cy)
        dbz = c.get("dbz", 20.0)
        c["label"] = chr(ord('A') + min(i, 25))
        print(f"Cluster #{i+1} [{c['label']}]: Centroid=(X:{cx}, Y:{cy}) BBox=(X:{min_x}..{max_x}, Y:{min_y}..{max_y}) dBZ={dbz:.1f}")

    # Generate tracking image using FonMaYang's production engine
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

    out_dir = "/Users/oatrice/.gemini/antigravity/brain/ca2a5939-fffa-4ac8-8124-6eb3a63b8135"
    out_path = os.path.join(out_dir, "ryg_radar_grid_overlay.png")
    with open(out_path, "wb") as f:
        f.write(img_bytes)

    print(f"\nSuccessfully generated aligned tracking image at: {out_path}")

if __name__ == "__main__":
    test_production_tracking_image()
