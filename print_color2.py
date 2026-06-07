import sys
import os
import cv2

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
from app.services.tmd_radar_processor import TMDRadarProcessor
from test_custom_image import extract_frames_from_gif

frames = extract_frames_from_gif('/Users/oatrice/Downloads/radar_nowcast_full (1).gif')
def preprocess_frame(f):
    if f.shape[1] != 800 or f.shape[0] != 800:
        f = cv2.resize(f, (800, 800), interpolation=cv2.INTER_NEAREST)
    return f
curr_frame = preprocess_frame(frames[-1])

for cy, cx in [(162, 413), (302, 444)]:
    print(f"Around {cx}, {cy}:")
    for dy in range(-5, 6):
        for dx in range(-5, 6):
            b, g, r = curr_frame[cy+dy, cx+dx]
            if r == 255 and g == 0 and b == 255:
                print(f"  Found exact Magenta at {cx+dx}, {cy+dy}")
