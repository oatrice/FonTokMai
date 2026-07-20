import json
import numpy as np
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.tmd_radar.clustering import TMDClusteringMixin
from app.services.tmd_radar.optical_flow import TMDOpticalFlow

def run():
    with open('backend/tests/fixtures/skn240_flow_fix.json', 'r') as f:
        data = json.load(f)
    
    flow = TMDOpticalFlow(station="skn240", mode="average", max_history=6)
    flow.frames = [np.array(f, dtype=np.uint8) for f in data["frames"]]
    
    ambient = TMDClusteringMixin.get_all_rain_clusters(
        frame=flow.frames[-1],
        flow=flow.flow_acc,
        user_x=486,
        user_y=390,
        scan_radius=None,
        min_dbz=10.0,
        cluster_dist=12,
        min_size=5
    )
    
    ambient.sort(key=lambda c: (-c.get("predicted_dbz", c.get("dbz_now", 20)), c.get("dist", 9999)))
    
    for i, c in enumerate(ambient[:10]):
        pixels = np.array(c['pixels'])
        min_y, min_x = pixels.min(axis=0)
        max_y, max_x = pixels.max(axis=0)
        print(f"Cluster {i}: size={len(pixels)} bbox=(x:{min_x}-{max_x}, y:{min_y}-{max_y}) dbz={c['dbz_now']}")

run()
