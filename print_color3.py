import sys
import os
import cv2

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
from app.services.tmd_radar_processor import TMDRadarProcessor
from test_custom_image import extract_frames_from_gif
frames = extract_frames_from_gif('/Users/oatrice/Downloads/radar_nowcast_full (1).gif')
curr_frame = cv2.resize(frames[-1], (800, 800), interpolation=cv2.INTER_NEAREST)

for cy, cx in [(164, 412), (300, 448)]:
    b, g, r = curr_frame[cy, cx]
    print(f"At {cx}, {cy}: BGR={b},{g},{r}")
