import numpy as np
import cv2
from datetime import datetime, timezone
from app.services.tmd_radar_processor import TMDRadarProcessor

def test_generate_radar_tracking_image_with_historical_wind_vectors():
    processor = TMDRadarProcessor("kkn240")
    # Synthetic frame: 800x800x3 uint8
    frame = np.zeros((800, 800, 3), dtype=np.uint8)
    user_x, user_y = 400, 400
    
    # Current cloud
    clouds = [{
        "cx": 380, "cy": 380,
        "vx": 5.0, "vy": 5.0,
        "dbz_now": 35.0, "dbz_prev": 30.0,
        "predicted_dbz": 35.0,
        "eta_min": 15.0,
        "growth_rate": 0.05,
        "dist": 30,
        "label": "A",
        "approaching": True
    }]
    
    # Historical vectors (3-5 past frames)
    historical_vectors = [
        {"cx": 350, "cy": 350, "vx": 4.0, "vy": 4.0, "dbz": 25.0},
        {"cx": 365, "cy": 365, "vx": 4.5, "vy": 4.5, "dbz": 30.0},
    ]
    
    time_utc = datetime(2026, 8, 14, 6, 20, tzinfo=timezone.utc)
    
    img_bytes = processor.generate_radar_tracking_image(
        frame=frame,
        user_x=user_x,
        user_y=user_y,
        clouds=clouds,
        time_utc=time_utc,
        historical_vectors=historical_vectors
    )
    
    assert img_bytes is not None
    assert len(img_bytes) > 0
    
    # Verify decoding image
    nparr = np.frombuffer(img_bytes, np.uint8)
    decoded = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    assert decoded is not None
    assert decoded.shape[0] > 0 and decoded.shape[1] > 0

def test_radar_image_timestamp_overlay():
    processor = TMDRadarProcessor("kkn240")
    frame = np.zeros((800, 800, 3), dtype=np.uint8)
    user_x, user_y = 400, 400
    clouds = [{
        "cx": 400, "cy": 400,
        "vx": 0.0, "vy": 0.0,
        "dbz_now": 30.0,
        "predicted_dbz": 30.0,
        "eta_min": 0.0,
        "dist": 0,
        "label": "A",
        "approaching": True
    }]
    time_utc = datetime(2026, 8, 14, 6, 30, tzinfo=timezone.utc)
    
    img_bytes = processor.generate_radar_tracking_image(
        frame=frame,
        user_x=user_x,
        user_y=user_y,
        clouds=clouds,
        time_utc=time_utc
    )
    assert img_bytes is not None
    nparr = np.frombuffer(img_bytes, np.uint8)
    decoded = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    assert decoded is not None
