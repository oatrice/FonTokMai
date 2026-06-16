import re

with open('backend/app/services/weather_manager.py', 'r') as f:
    content = f.read()

# Add imports at top
imports = """import logging
import asyncio
import cv2
import numpy as np
import io
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont
from typing import Optional
from app.dependencies import get_repo_context
from .tomorrow import TomorrowService
from .rainbow import RainbowService
from .xweather import XweatherService
from .open_meteo import OpenMeteoService
from .tmd_radar_processor import TMDRadarProcessor
"""

# Replace top imports
content = re.sub(r'import logging.*?(?=logger = logging\.getLogger)', imports, content, flags=re.DOTALL)

# Remove inner imports
content = re.sub(r'^\s*import asyncio\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*import cv2\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*import numpy as np\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*import io\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*from datetime import datetime, timedelta, timezone\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*from app\.dependencies import get_repo_context\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*from PIL import Image, ImageDraw, ImageFont\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*from zoneinfo import ZoneInfo\n', '', content, flags=re.MULTILINE)

# Add cache TTL logic
# Replace `self.tmd_frames_cache[station_code] = (frames, last_modified_dt)` with `(frames, last_modified_dt, time.time())`
content = content.replace('self.tmd_frames_cache[station_code] = (frames, last_modified_dt)', 'self.tmd_frames_cache[station_code] = (frames, last_modified_dt, time.time())')

# Replace the check:
old_check = """                if station_code in self.tmd_frames_cache:
                    frames, last_modified_dt = self.tmd_frames_cache[station_code]
                else:"""
new_check = """                # Check cache with 10-minute TTL to prevent stale frames across cron runs
                cached_data = self.tmd_frames_cache.get(station_code)
                if cached_data and (time.time() - cached_data[2]) < 600:
                    frames, last_modified_dt = cached_data[0], cached_data[1]
                else:"""
content = content.replace(old_check, new_check)

with open('backend/app/services/weather_manager.py', 'w') as f:
    f.write(content)
print("weather_manager.py fixed.")
