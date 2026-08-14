import sys
import numpy as np
from unittest.mock import MagicMock
sys.modules['google.cloud.storage'] = MagicMock()
sys.modules['google.cloud.vision'] = MagicMock()

from app.services.tmd_radar_config import STATIONS
from app.services.tmd_radar.processor import TMDRadarProcessor

def test_generate_radar_tracking_image_handles_out_of_bounds_user_coords():
    """Verify generate_radar_tracking_image does not crash with OpenCV resize error when user_x/user_y exceed frame bounds."""
    processor = TMDRadarProcessor("chn")
    frame_800 = np.ones((800, 800, 3), dtype=np.uint8) * 100
    
    # user_x=1326 is out of bounds for an 800x800 frame
    user_x = 1326
    user_y = 637
    clouds = []
    now_utc = None
    all_rain_clusters = [{"cx": 400, "cy": 400, "dbz": 25.0, "size": 20, "label": "A"}]
    predictions = []
    
    img_bytes = processor.generate_radar_tracking_image(
        frame=frame_800,
        user_x=user_x,
        user_y=user_y,
        clouds=clouds,
        time_utc=now_utc,
        all_rain_clusters=all_rain_clusters,
        predictions=predictions,
    )
    
    assert img_bytes is not None, "Should generate tracking image safely for out of bounds user coordinates"
    assert len(img_bytes) > 0
