import cv2
import numpy as np
from app.services.tmd_radar_processor import TMDRadarProcessor

def test_bug():
    # Let's recreate exactly what the user sees
    processor = TMDRadarProcessor("kkn120")
    
    # Fake frame 680x680
    frame = np.zeros((680, 680, 3), dtype=np.uint8)
    
    # User at 340, 340
    user_x, user_y = 340, 340
    
    # Cloud at 300, 300 moving to 340, 340
    cv2.circle(frame, (300, 300), 10, (0, 255, 0), -1)
    
    clouds = [{
        "cx": 300, "cy": 300,
        "vx": 4, "vy": 4, # moving right and down (towards 340, 340)
        "eta_min": 10,
        "predicted_dbz": 50
    }]
    
    processor.draw_pin_on_frame(frame, user_x, user_y)
    img_bytes = processor.generate_radar_tracking_image(frame, user_x, user_y, clouds)
    
    with open("tests/tracking_test.png", "wb") as f:
        f.write(img_bytes)
        
    print("Test image saved.")

if __name__ == '__main__':
    test_bug()
