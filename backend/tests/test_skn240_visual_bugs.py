import os
import math
import numpy as np
import pytest
import cv2
from app.services.tmd_radar.processor import TMDRadarProcessor
from app.services.weather_manager import _DEV_CONFIG

def _load_fixture() -> tuple:
    tests_dir = os.path.dirname(__file__)
    fixture_path = os.getenv("FIXTURE_PATH", os.path.join(tests_dir, "test_skn240_frames.npz"))
    if not os.path.exists(fixture_path):
        return None, None, None, None
    data = np.load(fixture_path, allow_pickle=True)
    frames = data["frames"]
    flow = data["flow"]
    flow_mode = str(data["flow_mode"])
    meta = data["meta"].item() if "meta" in data else {}
    return list(frames), flow, flow_mode, meta

@pytest.mark.asyncio
async def test_skn240_visual_fixes():
    frames, flow, flow_mode, meta = _load_fixture()
    assert frames is not None, "Fixture test_skn240_frames.npz not found!"
    
    # 1. Initialize Processor for skn240
    processor = TMDRadarProcessor("skn240")
    
    # 2. Get user coordinate (17.1712, 104.4594 -> Nong Khai/Sakon Nakhon crop area)
    user_x, user_y = processor.latlng_to_pixel(17.1712, 104.4594, is_loop=True)
    
    # 3. Find clusters with new cluster_dist params
    # ambient clouds: cluster_dist=6
    clusters = processor.get_all_rain_clusters(
        frame=frames[-1],
        flow=flow,
        user_x=user_x,
        user_y=user_y,
        scan_radius=None,
        min_dbz=10.0,
        cluster_dist=6,
        min_size=5
    )
    
    # Assert that no clusters are found in the left margin area (X < 75)
    # The left colorbar is around X=54..68. If it's correctly masked, it shouldn't produce rain clusters.
    left_margin_clusters = [c for c in clusters if c["cx"] < 75]
    assert len(left_margin_clusters) == 0, f"Detected fake clusters on left margin colorbar legend: {left_margin_clusters}"
    
    # Assert that the bottom clusters are separated (we shouldn't have a single giant cluster of size > 8000)
    giant_clusters = [c for c in clusters if len(c.get("pixels", [])) > 8000]
    assert len(giant_clusters) == 0, "The giant rain cluster at the bottom wasn't split/separated!"
    
    # 4. Find approaching clouds (cluster_dist=10)
    clouds = processor.find_approaching_clouds(
        frames[-1], frames[-2], flow, user_x, user_y,
        search_radius=80,
        min_dbz=10.0,
        cluster_dist=10,
        hit_radius=20,
        cluster_min=3,
        dot_threshold=0.5
    )
    
    # Label them
    for i, c in enumerate(clusters):
        c["label"] = chr(ord('A') + min(i, 25))
        
    # Match labels
    for appr_c in clouds:
        matched_label = "?"
        min_d = 9999
        for amb_c in clusters:
            d = math.hypot(appr_c["cx"] - amb_c["cx"], appr_c["cy"] - amb_c["cy"])
            if d < 150 and d < min_d:
                min_d = d
                matched_label = amb_c.get("label", "?")
        appr_c["label"] = matched_label

    # Spy on _resolve_label_collisions
    captured_labels = []
    original_resolve = processor._resolve_label_collisions
    def spy_resolve(labels, obstacles, img_w, img_h, iterations=60):
        original_resolve(labels, obstacles, img_w, img_h, iterations)
        captured_labels.extend(labels)
    
    processor._resolve_label_collisions = spy_resolve

    # 5. Generate tracking image and verify label layout
    from datetime import datetime, timezone
    img_bytes = processor.generate_radar_tracking_image(
        frame=frames[-1],
        user_x=user_x,
        user_y=user_y,
        clouds=clouds,
        all_rain_clusters=clusters,
        time_utc=datetime.fromtimestamp(1784219585, timezone.utc),
        cluster_dist_approaching=10,
        cluster_dist_ambient=8
    )
    assert len(img_bytes) > 0

    # Assert that no two non-hidden labels overlap
    non_hidden = [lbl for lbl in captured_labels if not lbl.get('hidden')]
    overlap_found = False
    for i in range(len(non_hidden)):
        for j in range(i + 1, len(non_hidden)):
            lbl_i = non_hidden[i]
            lbl_j = non_hidden[j]
            
            w_i, h_i = lbl_i['w'], lbl_i['h']
            w_j, h_j = lbl_j['w'], lbl_j['h']
            x1_i, y1_i = lbl_i['cx'] - w_i/2, lbl_i['cy'] - h_i/2
            x2_i, y2_i = lbl_i['cx'] + w_i/2, lbl_i['cy'] + h_i/2
            x1_j, y1_j = lbl_j['cx'] - w_j/2, lbl_j['cy'] - h_j/2
            x2_j, y2_j = lbl_j['cx'] + w_j/2, lbl_j['cy'] + h_j/2
            
            # Intersection
            ix1 = max(x1_i, x1_j)
            iy1 = max(y1_i, y1_j)
            ix2 = min(x2_i, x2_j)
            iy2 = min(y2_i, y2_j)
            
            if ix1 < ix2 and iy1 < iy2:
                overlap_found = True
                print(f"Overlap detected: {lbl_i['text']} and {lbl_j['text']} at i=({lbl_i['cx']}, {lbl_i['cy']}), j=({lbl_j['cx']}, {lbl_j['cy']})")
                
    assert not overlap_found, "Label collision detected!"

    # 6. Fragmentation Check: check Mukdahan cluster contours count after morph close
    crop_r = 120
    x1 = max(0, user_x - crop_r)
    y1 = max(0, user_y - crop_r)
    scale = 3.0
    
    giant_mukdahan = [c for c in clusters if c["cx"] > 480 and c["cy"] > 430 and len(c.get("pixels", [])) > 2000]
    assert len(giant_mukdahan) > 0, "Could not find the giant Mukdahan rain cluster!"
    c = giant_mukdahan[0]
    
    pts = np.array([[(int((px - x1) * scale), int((py - y1) * scale))] for px, py in c["pixels"]], dtype=np.int32)
    bx, by, bw, bh = cv2.boundingRect(pts)
    margin = 2
    mask_w, mask_h = bw + 2 * margin, bh + 2 * margin
    mask = np.zeros((mask_h, mask_w), dtype=np.uint8)
    local_pts = pts - np.array([[[bx - margin, by - margin]]], dtype=np.int32)
    for pt in local_pts:
        px, py = pt[0]
        if 0 <= px < mask_w and 0 <= py < mask_h:
            mask[py, px] = 255
            
    # Closed mask using the scale-aware kernel
    ksize = int(8 * scale)
    if ksize % 2 == 0:
        ksize += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))
    mask_closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    min_area_px = 10.0 / ((processor.config.bbox.lng_max - processor.config.bbox.lng_min) * 111.0 / 800.0) ** 2
    valid_contours = [ctr for ctr in contours if cv2.contourArea(ctr) >= min_area_px]
    
    assert len(valid_contours) <= 3, f"Fragmentation detected: {len(valid_contours)} contours found for the giant cluster"
