import cv2
import numpy as np
import os
import sys

def draw_c4_visual():
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
    
    # C4: Column C (index 2), Row 4 (index 3)
    col_idx = 2
    row_idx = 3
    
    x1 = int(crop_x1 + col_idx * cell_w)
    x2 = int(crop_x1 + (col_idx + 1) * cell_w)
    y1 = int(crop_y1 + row_idx * cell_h)
    y2 = int(crop_y1 + (row_idx + 1) * cell_h)
    
    print(f"C4 Pixel Coordinates in raw image: X in [{x1}, {x2}], Y in [{y1}, {y2}]")
    
    # Crop the C4 region (30x30 pixels)
    c4_crop = frame[y1:y2, x1:x2].copy()
    
    # We want to show a slightly larger region to give context (B3, C3, D3, B4, C4, D4, B5, C5, D5)
    # Crop 3x3 cells centered at C4
    cx1 = int(crop_x1 + (col_idx - 1) * cell_w)
    cx2 = int(crop_x1 + (col_idx + 2) * cell_w)
    cy1 = int(crop_y1 + (row_idx - 1) * cell_h)
    cy2 = int(crop_y1 + (row_idx + 2) * cell_h)
    
    context_crop = frame[cy1:cy2, cx1:cx2].copy()
    
    # Draw a red border around the C4 cell in the context crop
    # In context crop, C4 starts at relative coordinates (30, 30) to (60, 60)
    cv2.rectangle(context_crop, (30, 30), (60, 60), (0, 0, 255), 1)
    
    # Let's scale up both images by 10x for visual clarity
    c4_zoomed = cv2.resize(c4_crop, (300, 300), interpolation=cv2.INTER_NEAREST)
    context_zoomed = cv2.resize(context_crop, (900, 900), interpolation=cv2.INTER_NEAREST)
    
    # Add text labels on the context zoom
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(context_zoomed, "B3", (10, 25), font, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(context_zoomed, "C3 (Rain)", (310, 25), font, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(context_zoomed, "D3", (610, 25), font, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(context_zoomed, "B4 (Rain)", (10, 325), font, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(context_zoomed, "C4 (Target)", (310, 325), font, 0.6, (0, 0, 255), 1, cv2.LINE_AA)
    cv2.putText(context_zoomed, "D4", (610, 325), font, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    
    # Save the output images
    c4_path = os.path.join(tests_dir, "c4_crop.png")
    context_path = os.path.join(tests_dir, "c4_context.png")
    
    cv2.imwrite(c4_path, c4_zoomed)
    cv2.imwrite(context_path, context_zoomed)
    
    print(f"\nSaved C4 crop image to: {os.path.abspath(c4_path)}")
    print(f"Saved C4 context image (3x3 cells, C4 bordered in red) to: {os.path.abspath(context_path)}")

if __name__ == "__main__":
    draw_c4_visual()
