import cv2
from app.services.tmd_radar.clustering import TMDClusteringMixin
from app.services.tmd_radar_config import DBZ_COLOR_MAPPING, IGNORED_COLORS
import math

img = cv2.imread('backend/tests/test_tracking_out.png') # wait, need the actual radar frame
# Wait, the test script downloads radar frames to a fixture.
