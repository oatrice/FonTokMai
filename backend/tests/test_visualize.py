import cv2
import numpy as np
from app.services.tmd_radar_processor import TMDRadarProcessor

def test_visual():
    frame = np.zeros((1000, 1000, 3), dtype=np.uint8)
    
    # Draw a mock cloud at 400, 400
    cv2.circle(frame, (400, 400), 20, (255, 0, 0), -1)
    
    # Draw a mock cloud at 550, 450
    cv2.circle(frame, (550, 450), 30, (0, 0, 255), -1)
    
    user_x, user_y = 500, 500
    
    clouds = [
        {"cx": 400, "cy": 400, "vx": 5, "vy": 5, "eta_min": 10, "predicted_dbz": 50},
        {"cx": 550, "cy": 450, "vx": -5, "vy": 0, "eta_min": 20, "predicted_dbz": 30}
    ]
    
    processor = TMDRadarProcessor("kkn120")
    # Add user pin
    processor.draw_pin_on_frame(frame, user_x, user_y)
    
    # Generate image
    img_bytes = processor.generate_radar_tracking_image(frame, user_x, user_y, clouds)
    
    import os
    out_path = os.path.join(os.path.dirname(__file__), "test_output.png")
    with open(out_path, "wb") as f:
        f.write(img_bytes)

if __name__ == '__main__':
    test_visual()
