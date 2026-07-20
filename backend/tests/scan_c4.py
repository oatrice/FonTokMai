import cv2
import numpy as np
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.tmd_radar_processor import TMDRadarProcessor
from app.services.tmd_radar_config import DBZ_COLOR_MAPPING, IGNORED_COLORS

def scan_c4_pixels():
    tests_dir = os.path.dirname(__file__)
    gif_path = os.path.join(tests_dir, "test_kkn240.gif")
    
    cap = cv2.VideoCapture(gif_path)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("Failed to read frame.")
        return
        
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # User is at 251, 219
    # C4 X-range: [191, 221], Y-range: [189, 219]
    print("Scanning C4 region (X: 191-221, Y: 189-219) for active rain pixels:")
    
    rain_pixels_count = 0
    non_zero_dbz = []
    
    for y in range(189, 220):
        for x in range(191, 221):
            pixel = frame_rgb[y, x]
            r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
            
            # Map dBZ using the static processor logic
            dbz = TMDRadarProcessor._get_dbz_at_pixel_static(frame_rgb, x, y)
            if dbz > 0:
                rain_pixels_count += 1
                non_zero_dbz.append((x, y, (r, g, b), dbz))
                
    print(f"Total rain pixels found in C4: {rain_pixels_count} / {30*31} pixels")
    if non_zero_dbz:
        print("\nFirst 10 detected rain pixels in C4:")
        for px in non_zero_dbz[:10]:
            print(f"At ({px[0]}, {px[1]}) RGB={px[2]} -> dbz={px[3]}")
    else:
        # If no rain, print what colors are actually in C4 so we can see why it didn't map
        print("\nNo rain detected. Sampling some background colors in C4:")
        sample_colors = {}
        for y in range(189, 220, 3):
            for x in range(191, 221, 3):
                pixel = frame_rgb[y, x]
                rgb = (int(pixel[0]), int(pixel[1]), int(pixel[2]))
                sample_colors[rgb] = sample_colors.get(rgb, 0) + 1
        
        sorted_samples = sorted(sample_colors.items(), key=lambda k: k[1], reverse=True)
        for rgb, count in sorted_samples[:10]:
            print(f"RGB={rgb}: {count} times")

if __name__ == "__main__":
    scan_c4_pixels()
