import pytest
import numpy as np
import cv2
from app.services.tmd_radar_processor import TMDRadarProcessor

def test_generate_radar_tracking_image_clean_mode():
    frame = np.zeros((600, 600, 3), dtype=np.uint8)
    cv2.circle(frame, (300, 300), 20, (0, 0, 255), -1)
    
    user_x, user_y = 300, 300
    clouds = [
        {"cx": 250, "cy": 250, "vx": 2, "vy": 2, "eta_min": 15, "predicted_dbz": 45, "id": "A1"}
    ]
    predictions = [
        {"src_x": 250, "src_y": 250, "dbz": 45, "time_offset": 0},
        {"src_x": 270, "src_y": 270, "dbz": 40, "time_offset": 15},
        {"src_x": 290, "src_y": 290, "dbz": 35, "time_offset": 30},
    ]

    processor = TMDRadarProcessor("skn240")
    
    # Test with show_labels=False
    img_bytes_clean = processor.generate_radar_tracking_image(
        frame=frame,
        user_x=user_x,
        user_y=user_y,
        clouds=clouds,
        predictions=predictions,
        show_clouds=True,
        show_trajectory=True,
        show_labels=False
    )
    
    assert img_bytes_clean is not None
    assert isinstance(img_bytes_clean, bytes)
    assert len(img_bytes_clean) > 0


@pytest.mark.asyncio
async def test_rain_minimal_command_router():
    from app.routers.webhook_commands import handle_rain_minimal_command
    assert callable(handle_rain_minimal_command)
