import re

with open('backend/app/services/tmd_radar_processor.py', 'r') as f:
    content = f.read()

# Hoist imports
new_imports = """import cv2
import numpy as np
import os
import io
import time
import math
import httpx
from typing import List, Tuple, Optional
from datetime import datetime, timezone
from google.cloud import storage
from PIL import Image, ImageSequence
from app.services.ocr_service import OCRService
from app.dependencies import get_repo_context
from app.services.tmd_radar_config import STATIONS, DBZ_COLOR_MAPPING, IGNORED_COLORS
"""

content = re.sub(r'^import cv2.*?from app\.services\.tmd_radar_config import STATIONS, DBZ_COLOR_MAPPING, IGNORED_COLORS\n', new_imports, content, flags=re.DOTALL | re.MULTILINE)

content = re.sub(r'^\s*import os\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*import math\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*import cv2\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*import httpx\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*import time\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*import io\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*from datetime import datetime, timezone\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*from google\.cloud import storage\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*from app\.dependencies import get_repo_context\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*from PIL import Image, ImageSequence\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*from app\.services\.ocr_service import OCRService\n', '', content, flags=re.MULTILINE)

with open('backend/app/services/tmd_radar_processor.py', 'w') as f:
    f.write(content)
print("tmd_radar_processor.py fixed.")
