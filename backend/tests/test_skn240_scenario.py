import cv2
import numpy as np
from app.services.tmd_radar_processor import TMDRadarProcessor
import os

def test_scenario():
    processor = TMDRadarProcessor("skn240")
    
    # Fake frame 800x800 (standard for skn240)
    frame = np.zeros((800, 800, 3), dtype=np.uint8)
    
    # Draw some fake terrain/map just so it's not totally black
    # cv2.rectangle(frame, (0, 0), (800, 800), (30, 30, 30), -1)
    
    # User at 17.255266, 104.773468
    user_x, user_y = processor.latlng_to_pixel(17.255266, 104.773468)
    # 456, 320
    
    # Cloud A: Approaching, big cloud with a hull
    # Cloud A centroid
    cxA, cyA = user_x - 60, user_y - 80
    pixels_A = []
    for dx in range(-30, 30, 2):
        for dy in range(-20, 40, 2):
            if (dx*dx/900 + dy*dy/1600) <= 1:
                pixels_A.append((cxA + dx, cyA + dy))
                cv2.circle(frame, (cxA + dx, cyA + dy), 1, (0, 255, 255), -1)
                
    # Cloud B: Ambient (not approaching), small cloud
    cxB, cyB = user_x + 90, user_y - 20
    pixels_B = []
    for dx in range(-15, 15, 2):
        for dy in range(-15, 15, 2):
            if (dx*dx/225 + dy*dy/225) <= 1:
                pixels_B.append((cxB + dx, cyB + dy))
                cv2.circle(frame, (cxB + dx, cyB + dy), 1, (0, 100, 255), -1)

    clouds = [
        {
            "label": "A",
            "cx": cxA, "cy": cyA,
            "vx": 3.0, "vy": 4.0, # moving towards user_x, user_y
            "eta_min": 15,
            "dbz_now": 35.0,
            "predicted_dbz": 45.0,
            "approaching": True,
            "pixels": pixels_A,
            "dist": 100.0,
            "growth_rate": 0.1
        },
        {
            "label": "B",
            "cx": cxB, "cy": cyB,
            "vx": 1.0, "vy": -1.0, # moving away
            "eta_min": 9999,
            "dbz_now": 20.0,
            "predicted_dbz": 20.0,
            "approaching": False,
            "pixels": pixels_B,
            "dist": 92.0,
            "growth_rate": -0.1
        }
    ]
    
    processor.draw_pin_on_frame(frame, user_x, user_y)
    
    # Using the time string in some commits requires now_utc but we can pass None or leave default if optional
    try:
        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc)
        img_bytes = processor.generate_radar_tracking_image(
            frame=frame, 
            user_x=user_x, 
            user_y=user_y, 
            clouds=[clouds[0]],  # display_clouds (approaching)
            time_utc=now_utc,
            all_rain_clusters=clouds # all clusters so ambient gets drawn
        )
    except TypeError:
        # Older commits might have a different signature
        try:
            img_bytes = processor.generate_radar_tracking_image(frame, user_x, user_y, [clouds[0]])
        except Exception:
            # Try just passing all of them if all_rain_clusters is not supported
            img_bytes = processor.generate_radar_tracking_image(frame, user_x, user_y, clouds)

    if img_bytes:
        out_path = os.path.join(os.path.dirname(__file__), "tracking_skn240_test.png")
        with open(out_path, "wb") as f:
            f.write(img_bytes)
        print("Saved tracking_skn240_test.png successfully.")
    else:
        print("Failed to generate image.")

if __name__ == '__main__':
    test_scenario()
