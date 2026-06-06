import cv2
import numpy as np
from app.services.tmd_radar_processor import TMDRadarProcessor

def test_generate_radar_tracking_image():
    # Create a dummy image 1000x1000
    frame = np.zeros((1000, 1000, 3), dtype=np.uint8)
    
    # Draw a "cloud" at (500, 500)
    cv2.circle(frame, (500, 500), 10, (0, 255, 0), -1)
    
    # User is at 450, 450
    user_x, user_y = 450, 450
    
    # Clouds list with one cloud at 500, 500
    clouds = [{
        "cx": 500, "cy": 500,
        "vx": 0, "vy": 0,
        "eta_min": 15,
        "predicted_dbz": 45
    }]
    
    # We want to see where the circle is actually drawn in the result image
    # Let's recreate the logic and inspect the crop
    crop_r = 120
    h, w = frame.shape[:2]
    x1 = max(0, user_x - crop_r)
    y1 = max(0, user_y - crop_r)
    x2 = min(w, user_x + crop_r)
    y2 = min(h, user_y + crop_r)
    
    crop_img = frame[y1:y2, x1:x2].copy()
    scale = 3.0
    img = cv2.resize(crop_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
    
    cx = int((500 - x1) * scale)
    cy = int((500 - y1) * scale)
    
    print(f"crop bounds: x1={x1}, x2={x2}, y1={y1}, y2={y2}")
    print(f"cloud original: 500, 500")
    print(f"cloud mapped: cx={cx}, cy={cy}")
    
    # In the scaled image, where is the green pixel from the original cloud?
    # Original cloud was at (500, 500)
    # In crop_img, it is at (500-x1, 500-y1) = (170, 170)
    # In scaled img, the green pixels should be around (170*3, 170*3) = (510, 510)
    # Let's check the pixel value at cx, cy in img
    b, g, r = img[cy, cx]
    print(f"Pixel at cx, cy: B={b}, G={g}, R={r}")
    
    if g > 200:
        print("MAPPING IS PERFECT.")
    else:
        print("MAPPING IS WRONG!")

if __name__ == '__main__':
    test_generate_radar_tracking_image()
