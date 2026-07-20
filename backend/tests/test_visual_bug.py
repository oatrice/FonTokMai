import numpy as np
from app.services.tmd_radar_processor import TMDRadarProcessor

def test_get_all_rain_clusters_peak_detection():
    processor = TMDRadarProcessor("kkn120")
    
    # 680x680 frame for crop bounds
    frame = np.zeros((680, 680, 3), dtype=np.uint8)
    flow = np.zeros((680, 680, 2), dtype=np.float32)
    
    # Place a cloud cluster: a line of pixels at y=300, from x=200 to 240
    # The brightest pixel (highest dBZ) will be at x=230 (Red pixel)
    # We draw it 3 pixels thick to survive the median blur in extract_rain_mask.
    # The peak (Red) is also 3 pixels wide (229-231) to survive median blur.
    for y in range(299, 302):
        for x in range(200, 241, 1):
            if 229 <= x <= 231:
                frame[y, x] = [255, 0, 0] # Peak dBZ (Red)
            elif 221 <= x <= 228:
                frame[y, x] = [255, 255, 0] # Medium dBZ (Yellow)
            else:
                frame[y, x] = [0, 255, 0] # Lower dBZ (Green)

    user_x, user_y = 300, 300
    
    # Run get_all_rain_clusters
    clusters = processor.get_all_rain_clusters(
        frame=frame,
        flow=flow,
        user_x=user_x,
        user_y=user_y,
        scan_radius=250,
        cluster_dist=10
    )
    
    assert len(clusters) == 1, f"Expected 1 cluster, got {len(clusters)}"
    c = clusters[0]
    
    # Centroid cx should be around the weighted average
    assert "cx" in c
    assert "cy" in c
    
    # Peak cx/cy must be exactly at x=230, y=300 (the brightest point)
    assert "peak_cx" in c, "peak_cx missing from cluster info"
    assert "peak_cy" in c, "peak_cy missing from cluster info"
    assert c["peak_cx"] in [229, 230, 231], f"Expected peak_cx near 230, got {c['peak_cx']}"
    assert c["peak_cy"] in [299, 300, 301], f"Expected peak_cy near 300, got {c['peak_cy']}"
    
    print("PEAK DETECTION TEST PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_get_all_rain_clusters_peak_detection()
