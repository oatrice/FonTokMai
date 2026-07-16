import cv2
import numpy as np
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.tmd_radar_processor import TMDRadarProcessor

def analyze_c4_pixels_detailed():
    tests_dir = os.path.dirname(__file__)
    gif_path = os.path.join(tests_dir, "test_kkn240.gif")
    
    cap = cv2.VideoCapture(gif_path)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("Failed to read frame.")
        return
        
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Grid parameters
    crop_x1, crop_y1 = 131, 99
    cell_w, cell_h = 30.0, 30.0
    
    # coordinates for C4 (Col index 2, Row index 3)
    c4_x1, c4_y1 = int(crop_x1 + 2*cell_w), int(crop_y1 + 3*cell_h)
    c4_x2, c4_y2 = int(crop_x1 + 3*cell_w), int(crop_y1 + 4*cell_h)
    
    # coordinates for D4 (Col index 3, Row index 3) - Clear background reference
    d4_x1, d4_y1 = int(crop_x1 + 3*cell_w), int(crop_y1 + 3*cell_h)
    d4_x2, d4_y2 = int(crop_x1 + 4*cell_w), int(crop_y1 + 4*cell_h)
    
    c4_pixels = frame_rgb[c4_y1:c4_y2, c4_x1:c4_x2].reshape(-1, 3)
    d4_pixels = frame_rgb[d4_y1:d4_y2, d4_x1:d4_x2].reshape(-1, 3)
    
    print("=== C4 DETAILED PIXEL ANALYSIS ===")
    print(f"C4 size: {len(c4_pixels)} pixels")
    print(f"D4 (Reference Clear Cell) size: {len(d4_pixels)} pixels\n")
    
    # Calculate unique colors and their frequency
    def get_color_freq(pixels):
        freq = {}
        for p in pixels:
            t = (int(p[0]), int(p[1]), int(p[2]))
            freq[t] = freq.get(t, 0) + 1
        return freq

    c4_freq = get_color_freq(c4_pixels)
    d4_freq = get_color_freq(d4_pixels)
    
    # Group unique colors in C4 that DO NOT exist in D4 (potential clouds / edges)
    novel_colors = {}
    for color, count in c4_freq.items():
        if color not in d4_freq:
            novel_colors[color] = count
            
    print("--- 1. Unique Colors in C4 (Not present in background cell D4) ---")
    sorted_novel = sorted(novel_colors.items(), key=lambda k: k[1], reverse=True)
    if sorted_novel:
        for rgb, count in sorted_novel[:15]:
            # Convert to HSV to check hue (e.g. is it close to green, blue, yellow?)
            hsv = cv2.cvtColor(np.uint8([[rgb]]), cv2.COLOR_RGB2HSV)[0][0]
            print(f"RGB={rgb} (HSV Hue={hsv[0]}, Sat={hsv[1]}, Val={hsv[2]}): found {count} times")
    else:
        print("No unique colors compared to D4.")
        
    print("\n--- 2. Top 5 dominant colors in C4 ---")
    sorted_c4 = sorted(c4_freq.items(), key=lambda k: k[1], reverse=True)
    for rgb, count in sorted_c4[:5]:
        print(f"RGB={rgb}: {count} times")
        
    print("\n--- 3. Top 5 dominant colors in D4 (Clear Background) ---")
    sorted_d4 = sorted(d4_freq.items(), key=lambda k: k[1], reverse=True)
    for rgb, count in sorted_d4[:5]:
        print(f"RGB={rgb}: {count} times")

if __name__ == "__main__":
    analyze_c4_pixels_detailed()
