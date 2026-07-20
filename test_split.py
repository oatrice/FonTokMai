import sys
sys.path.append('backend')
from app.services.tmd_radar.clustering import get_all_rain_clusters
import numpy as np

# Let's just modify test_kkn240_run.py to test min_dbz=15.0 and cluster_dist=6
