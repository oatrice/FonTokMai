import numpy as np
from app.services.tmd_radar_processor import TMDRadarProcessor

def test_find_approaching_clouds_clustering():
    processor = TMDRadarProcessor("kkn120")
    
    # Frame must be at least 680x680 so pixels fall within the valid crop zone:
    # kkn120: loop_crop_x=80, loop_crop_y=40, loop_crop_width=600, loop_crop_height=600
    # Valid area: x in [80, 680), y in [40, 640)
    frame = np.zeros((680, 680, 3), dtype=np.uint8)
    flow = np.zeros((680, 680, 2), dtype=np.float32)
    flow[..., 0] = 5.0  # all moving right (positive dx toward user_x > cloud_x)
    
    # Place a contiguous cloud from x=200 to x=280 at y=300 (inside valid zone)
    # Use RGB (255, 0, 0) = Red = 50 dBZ (frames are in RGB format from PIL)
    # True centroid_x = (200+280)/2 = 240
    for x in range(200, 281, 2):
        frame[300, x] = [255, 0, 0]  # RGB Red = 50.0 dBZ
    
    # User is to the right of the cloud, cloud moving right => approaching
    user_x, user_y = 400, 300
    
    clouds = processor.find_approaching_clouds(
        frame, frame, flow, user_x, user_y,
        search_radius=250, min_dbz=20.0, cluster_dist=5
    )
    
    assert len(clouds) == 1, f"Expected 1 clustered cloud, got {len(clouds)}"
    assert clouds[0]['cx'] == 240, f"Expected centroid at 240, got {clouds[0]['cx']}"
    print("TEST PASSED")

if __name__ == '__main__':
    test_find_approaching_clouds_clustering()
