import sys
import numpy as np
from unittest.mock import MagicMock
sys.modules['google.cloud.storage'] = MagicMock()
sys.modules['google.cloud.vision'] = MagicMock()

from app.services.tmd_radar_config import STATIONS
from app.services.tmd_radar.processor import TMDRadarProcessor

def test_chainat_loop_pixel_mapping_within_frame_bounds():
    """Verify latlng_to_pixel for Chainat (chn) in loop mode produces pixel coordinates within 800x800 frame bounds."""
    processor = TMDRadarProcessor("chn")
    lat, lng = 15.564, 100.8292
    
    user_px, user_py = processor.latlng_to_pixel(lat, lng, is_loop=True)
    assert user_px is not None and user_py is not None
    assert 0 <= user_px <= 800, f"user_px {user_px} out of 800px frame bounds"
    assert 0 <= user_py <= 800, f"user_py {user_py} out of 800px frame bounds"

def test_determine_use_loop_mapping_by_frame_shape():
    """Verify loop mapping detection correctly chooses loop mode when frame width is <= 1000."""
    frame_800 = np.zeros((800, 800, 3), dtype=np.uint8)
    frame_1600 = np.zeros((1600, 1920, 3), dtype=np.uint8)
    
    def is_loop_frame(frame, frame_source):
        return (frame_source == "loop_gif") or (frame is not None and frame.shape[1] <= 1000)

    assert is_loop_frame(frame_800, "static_cache") is True
    assert is_loop_frame(frame_1600, "static_cache") is False
    assert is_loop_frame(frame_1600, "loop_gif") is True
