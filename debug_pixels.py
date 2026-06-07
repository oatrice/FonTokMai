import sys
import os
import math
import cv2
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
from app.services.tmd_radar_processor import TMDRadarProcessor
from test_custom_image import extract_frames_from_gif

processor = TMDRadarProcessor("kkn240")
user_x_1280, user_y_1280 = 711, 346
px = int(user_x_1280 * 800 / 1280)
py = int(user_y_1280 * 800 / 1280)

frames = extract_frames_from_gif('/Users/oatrice/Downloads/radar_nowcast_full (1).gif')

def preprocess_frame(f):
    if f.shape[1] != 800 or f.shape[0] != 800:
        f = cv2.resize(f, (800, 800), interpolation=cv2.INTER_NEAREST)
    return f

curr_frame = preprocess_frame(frames[-1])
prev_frame = preprocess_frame(frames[-2])
curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
flow = cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)

check_x, check_y = px, py

print(f"User is at px={px}, py={py}")
print(f"Scanning entire area for Yellow pixels (30-35 dBZ)")

passed_pixels = []

for ty in range(0, curr_frame.shape[0]):
    for tx in range(0, curr_frame.shape[1]):
        dbz = processor.get_dbz_at_pixel(curr_frame, tx, ty)
        if dbz >= 30.0 and dbz <= 35.0:
            vx, vy = processor.get_flow_vector_at(flow, tx, ty)
            to_x = px - tx
            to_y = py - ty
            dist = math.sqrt(to_x**2 + to_y**2)
            if dist > 160: continue # Only care within search radius
            dot = (vx * to_x + vy * to_y) / dist if dist > 0 else 0
            v_mag = math.sqrt(vx**2 + vy**2)
            perp_dist = abs(to_x * vy - to_y * vx) / v_mag if v_mag > 0 else 0
            
            # Check neighbors
            neighbors = 0
            for dy_n in [-1, 0, 1]:
                for dx_n in [-1, 0, 1]:
                    if dx_n == 0 and dy_n == 0: continue
                    nx, ny = tx + dx_n, ty + dy_n
                    if 0 <= nx < curr_frame.shape[1] and 0 <= ny < curr_frame.shape[0]:
                        if processor.get_dbz_at_pixel(curr_frame, nx, ny) >= 20.0:
                            neighbors += 1
                            
            reason = "PASS"
            if neighbors < 1: reason = "FAIL: Neighbors"
            elif dot <= 0: reason = "FAIL: Dot"
            elif v_mag < 0.1: reason = "FAIL: Vmag"
            elif perp_dist > 15: reason = f"FAIL: CTE {perp_dist:.2f}"
            
            print(f"  Yellow at {tx},{ty} (dist={dist:.1f}) | dBZ={dbz} | neighbors={neighbors} | dot={dot:.2f} | cte={perp_dist:.2f} -> {reason}")
            if reason == "PASS":
                passed_pixels.append((tx, ty, dbz))

print(f"\nTotal passed Yellow pixels: {len(passed_pixels)}")
