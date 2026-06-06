import cv2
import numpy as np
from app.services.tmd_radar_processor import TMDRadarProcessor

def test_find_approaching_clouds_clustering():
    processor = TMDRadarProcessor("kkn120")
    
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    flow = np.zeros((100, 100, 2), dtype=np.float32)
    flow[..., 0] = 5.0 # all moving right (towards user at 100, 50)
    
    user_x, user_y = 100, 50
    
    # Create a contiguous cloud from x=20 to x=60 at y=50.
    # The true centroid is x=40.
    for x in range(20, 61, 2):
        frame[50, x] = [0, 0, 255] # BGR [0, 0, 255] -> RGB (255, 0, 0) -> 50.0 dBZ
        
    clouds = processor.find_approaching_clouds(
        frame, frame, flow, user_x, user_y,
        search_radius=80, min_dbz=20.0, cluster_dist=5
    )
    
    assert len(clouds) == 1, "Expected exactly 1 clustered cloud"
    assert clouds[0]['cx'] == 40, f"Expected centroid at 40, got {clouds[0]['cx']}"
    print("TEST PASSED")

if __name__ == '__main__':
    test_find_approaching_clouds_clustering()
