import json
import numpy as np
import sys
import os
import cv2

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.tmd_radar_processor import TMDRadarProcessor
from app.services.tmd_radar.clustering import TMDClusteringMixin

def run():
    # Don't even need processor! Just load the array!
    data = np.load('backend/tests/test_kkn240_frames.npz')
    # Actually wait, extract_rain_mask handles 3D arrays automatically!
    frame = data['frames'][-1]

    mask = TMDClusteringMixin.extract_rain_mask(None, frame)
    print(f"Mask at (317, 6) [y=6, x=317]: {mask[6, 317]}")
    
    min_dbz = 10.0
    cluster_dist = 12
    min_intensity = int(min_dbz * 4)
    rain_pixels = mask >= min_intensity
    print(f"Rain pixel at y=6, x=317: {rain_pixels[6, 317]}")
    
    bin_mask = (rain_pixels * 255).astype(np.uint8)
    ksize = cluster_dist if cluster_dist % 2 != 0 else cluster_dist + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))
    closed_mask = cv2.morphologyEx(bin_mask, cv2.MORPH_CLOSE, kernel)
    print(f"Closed mask at y=6, x=317: {closed_mask[6, 317]}")
    
    contours, _ = cv2.findContours(closed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"Total contours: {len(contours)}")
    
    found_in_contour = False
    for i, ctr in enumerate(contours):
        x, y, cw, ch = cv2.boundingRect(ctr)
        if x <= 317 <= x+cw and y <= 6 <= y+ch:
            print(f"Point found inside bounding box of contour {i}! x:{x}-{x+cw}, y:{y}-{y+ch}")

run()
