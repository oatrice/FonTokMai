import re
import os

with open('backend/app/services/tmd_radar/tracking.py', 'r') as f:
    tr_src = f.read()
with open('backend/app/services/tmd_radar/multiframe.py', 'r') as f:
    mf_src = f.read()

def extract_class_def(src, method_name):
    pattern = r'(?m)^    (?:@staticmethod\n    )?def ' + method_name + r'\(.*?(?=\n    (?:@staticmethod\n    )?def |\nclass |\Z)'
    match = re.search(pattern, src, re.DOTALL)
    if match:
        return match.group(0), src.replace(match.group(0), '')
    return None, src

def extract_top_def(src, method_name):
    pattern = r'(?m)^def ' + method_name + r'\(.*?(?=\ndef |\nclass |\Z)'
    match = re.search(pattern, src, re.DOTALL)
    if match:
        # indent it by 4 spaces to put inside a class
        indented = "\n".join("    " + line if line else "" for line in match.group(0).split('\n'))
        # mark as staticmethod
        indented = "    @staticmethod\n" + indented
        return indented, src.replace(match.group(0), '')
    return None, src

methods = []

# Top level functions from tracking.py
for name in ['_load_thai_font', '_chaikin_smooth', '_draw_neon_contours', '_contour_proximity_km']:
    m, tr_src = extract_top_def(tr_src, name)
    if m: methods.append(m)

# Class methods from tracking.py
for name in ['generate_radar_tracking_image', 'generate_timeline_image', 'render_rain_summary', 'draw_pin_on_frame', '_resolve_label_collisions']:
    m, tr_src = extract_class_def(tr_src, name)
    if m: methods.append(m)

# Class methods from multiframe.py
for name in ['generate_multiframe_analysis_image']:
    m, mf_src = extract_class_def(mf_src, name)
    if m: methods.append(m)

imports = """import os
import asyncio
import time
import logging
import math
import io
import re
import cv2
import httpx
import numpy as np
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageSequence, ImageFilter
from zoneinfo import ZoneInfo
from typing import List, Tuple, Optional
from app.services.tmd_radar_config import STATIONS, DBZ_COLOR_MAPPING, IGNORED_COLORS
from app.services.tmd_radar.renderer import RadarRenderer

logger = logging.getLogger(__name__)

class DefaultRadarRenderer(RadarRenderer):
    def __init__(self, processor=None):
        self.processor = processor
"""

for i, m in enumerate(methods):
    if m:
        m = m.replace("self.config", "self.processor.config")
        m = m.replace("self.station_code", "self.processor.station_code")
        # For top level functions that are now staticmethods, we need to replace calls to them with self.
        imports += "\n" + m + "\n"

imports = imports.replace("_load_thai_font(", "self._load_thai_font(")
imports = imports.replace("_chaikin_smooth(", "self._chaikin_smooth(")
imports = imports.replace("_draw_neon_contours(", "self._draw_neon_contours(")
imports = imports.replace("_contour_proximity_km(", "self._contour_proximity_km(")

with open('backend/app/services/tmd_radar/renderer_impl.py', 'w') as f:
    f.write(imports)

with open('backend/app/services/tmd_radar/tracking.py', 'w') as f:
    f.write(tr_src)

with open('backend/app/services/tmd_radar/multiframe.py', 'w') as f:
    f.write(mf_src)

print("Generated renderer_impl.py and cleaned up tracking.py and multiframe.py")
