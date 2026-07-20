import cv2
import numpy as np
import math
from app.services.weather_manager import _DEV_CONFIG
from app.services.tmd_radar_processor import TMDRadarProcessor
from app.services.tmd_radar_config import DBZ_COLOR_MAPPING, IGNORED_COLORS

def get_clusters(cluster_dist):
    data = np.load("backend/tests/test_kkn240_frames.npz", allow_pickle=True)
    frames = data["frames"]
    last_frame = frames[-1]
    flow = data["flow"]
    
    # user location 17.1712, 104.4594
    processor = TMDRadarProcessor("skn240")
    user_x, user_y = processor.latlng_to_pixel(17.1712, 104.4594, is_loop=True)
    
    clusters = processor.get_all_rain_clusters(
        frame=last_frame,
        flow=flow,
        user_x=user_x,
        user_y=user_y,
        scan_radius=200,
        min_dbz=10.0,
        cluster_dist=cluster_dist,
        min_size=5
    )
    
    print(f"\n--- cluster_dist={cluster_dist} ---")
    clusters.sort(key=lambda c: (-c.get("predicted_dbz", c.get("dbz_now", 20)), c.get("dist", 9999)))
    
    for i, c in enumerate(clusters[:10]):
        print(f"Cluster {chr(65+i)}: Centroid=({c['cx']}, {c['cy']}), Peak=({c.get('peak_cx')}, {c.get('peak_cy')}), Size={c['size']}, dBZ={c['dbz_now']}")
        
get_clusters(5)
get_clusters(8)
get_clusters(12)
get_clusters(15)
