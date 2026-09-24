import ast

with open('backend/app/services/weather_manager.py', 'r') as f:
    text = f.read()
    lines = text.split('\n')

class FuncExtractor(ast.NodeVisitor):
    def __init__(self):
        self.start = None
        self.end = None
    
    def visit_AsyncFunctionDef(self, node):
        if node.name == '_get_tmd_prediction':
            self.start = node.lineno
            self.end = node.end_lineno
        self.generic_visit(node)

tree = ast.parse(text)
extractor = FuncExtractor()
extractor.visit(tree)

if not extractor.start:
    print("Function not found")
    exit(1)

func_lines = lines[extractor.start-1:extractor.end]

# Modify func_lines to remove 'self' where it's not needed or forward to 'self.weather_manager'
new_func_lines = []
for line in func_lines:
    line = line.replace('self.get_active_radar_stations', 'self.weather_manager.get_active_radar_stations')
    line = line.replace('self.get_radar_status', 'self.weather_manager.get_radar_status')
    line = line.replace('self.load_persistent_cache_to_memory', 'self.weather_manager.load_persistent_cache_to_memory')
    line = line.replace('self.tmd_nowcast_override', 'self.weather_manager.tmd_nowcast_override')
    
    new_func_lines.append(line)

# Now, we put this into adapter.py
adapter_code = f"""from typing import Dict, Any, Optional
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import numpy as np

from app.services.tmd_radar.nowcast_port import NowcastPort
from app.services.tmd_radar.cache_manager import radar_cache
from app.services.tmd_radar_processor import TMDRadarProcessor
from app.services.weather_predictions import WeatherPredictionService
from app.services.tmd_radar_registry import get_radar_registry

logger = logging.getLogger(__name__)

class TMDNowcastAdapter(NowcastPort):
    def __init__(self, weather_manager):
        self.weather_manager = weather_manager

""" + "\n".join(["    " + line[4:] if line.startswith("    ") else "    " + line for line in new_func_lines])

with open('backend/app/services/tmd_radar/adapter.py', 'w') as f:
    f.write(adapter_code)

# Now replace the old function in weather_manager with a forward call
forward_call = """
    async def _get_tmd_prediction(self, lat: float, lng: float, force_station: Optional[str] = None) -> Optional[Dict[str, Any]]:
        from app.services.tmd_radar.adapter import TMDNowcastAdapter
        adapter = TMDNowcastAdapter(self)
        return await adapter.predict(lat, lng, force_station)
"""

new_wm = lines[:extractor.start-1] + forward_call.strip('\n').split('\n') + lines[extractor.end:]

with open('backend/app/services/weather_manager.py', 'w') as f:
    f.write("\n".join(new_wm))

