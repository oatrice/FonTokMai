import cv2
import numpy as np
from app.services.tmd_radar_processor import TMDRadarProcessor

processor = TMDRadarProcessor("skn240")
# We need 2 frames to calculate optical flow.
# But we don't have the previous frame locally.
# However, the user's log says "accuracy: 1.00", meaning it found clouds and did flow.
# I will just write a script to check if the user sent any other text.
