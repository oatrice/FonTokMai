import os
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
from app.dependencies import get_repo_context
from app.services.ocr_service import OCRService
try:
    from google.cloud import storage
except Exception:
    storage = None
from app.services.tmd_radar_config import STATIONS, DBZ_COLOR_MAPPING, IGNORED_COLORS

logger = logging.getLogger(__name__)






class TMDTrackingMixin:
    pass




