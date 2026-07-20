import cv2
import numpy as np
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.tmd_radar_processor import TMDRadarProcessor

def scan_all_grid_cells():
    tests_dir = os.path.dirname(__file__)
    gif_path = os.path.join(tests_dir, "test_kkn240.gif")
    
    cap = cv2.VideoCapture(gif_path)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("Failed to read frame.")
        return
        
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # User is at 251, 219 (Center of the 240x240 crop)
    # Grid starts at crop_x1 = user_x - 120 = 131
    # Grid starts at crop_y1 = user_y - 120 = 99
    crop_x1, crop_y1 = 131, 99
    cell_w, cell_h = 30.0, 30.0
    
    print("=== GRID CELLS SCAN (A1 - H8) ===")
    for row in range(8):
        for col in range(8):
            cell_name = f"{chr(ord('A') + col)}{row + 1}"
            
            x_min = int(crop_x1 + col * cell_w)
            x_max = int(crop_x1 + (col + 1) * cell_w)
            y_min = int(crop_y1 + row * cell_h)
            y_max = int(crop_y1 + (row + 1) * cell_h)
            
            # Count rain pixels in this cell
            rain_pixels = []
            for y in range(y_min, y_max):
                for x in range(x_min, x_max):
                    dbz = TMDRadarProcessor._get_dbz_at_pixel_static(frame_rgb, x, y)
                    if dbz > 0:
                        rain_pixels.append(dbz)
            
            if rain_pixels:
                max_dbz = max(rain_pixels)
                avg_dbz = sum(rain_pixels) / len(rain_pixels)
                print(f"Cell [{cell_name}]: Rain pixels={len(rain_pixels)}/{int(cell_w*cell_h)}, Max dBZ={max_dbz:.1f}, Avg dBZ={avg_dbz:.1f}")

if __name__ == "__main__":
    scan_all_grid_cells()
