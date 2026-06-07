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
print(f"Color at 413, 162: {curr_frame[162, 413]}")
print(f"Color at 444, 302: {curr_frame[302, 444]}")
