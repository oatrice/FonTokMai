import os
import math
import numpy as np
import pytest
from app.services.tmd_radar.processor import TMDRadarProcessor
from app.services.weather_manager import _DEV_CONFIG

def _load_fixture() -> tuple:
    tests_dir = os.path.dirname(__file__)
    fixture_path = os.path.join(tests_dir, "test_kkn240_frames.npz")
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
    assert frames is not None, "Fixture test_kkn240_frames.npz not found!"
    
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
    
    # 4. Find approaching clouds (cluster_dist=12)
    clouds = processor.find_approaching_clouds(
        frames[-1], frames[-2], flow, user_x, user_y,
        search_radius=80,
        min_dbz=10.0,
        cluster_dist=12,
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

    # 5. Generate tracking image and verify label layout
    # This will trigger _resolve_label_collisions
    from datetime import datetime, timezone
    img_bytes = processor.generate_radar_tracking_image(
        frame=frames[-1],
        user_x=user_x,
        user_y=user_y,
        clouds=clouds,
        all_rain_clusters=clusters,
        time_utc=datetime.fromtimestamp(1784219585, timezone.utc)
    )
    assert len(img_bytes) > 0
