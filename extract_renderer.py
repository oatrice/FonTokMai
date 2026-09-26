import re

tracking_file = 'backend/app/services/tmd_radar/tracking.py'
with open(tracking_file, 'r') as f:
    tracking_content = f.read()

multiframe_file = 'backend/app/services/tmd_radar/multiframe.py'
with open(multiframe_file, 'r') as f:
    multiframe_content = f.read()

# We need a proper script to parse and move functions, but maybe we can just make RadarRenderer a facade over processor for now?
