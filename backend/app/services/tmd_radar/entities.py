from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

class RainPrediction(BaseModel):
    time: str
    time_offset: int
    dbz: float
    rain: float
    src_x: int
    src_y: int

class RadarPredictionEntity(BaseModel):
    station_code: str
    predictions: List[RainPrediction]
    intensity: str
    max_rain: float
    max_dbz: float
    duration_minutes: int
    wind_speed_kmh: float
    wind_dir_text: str
    endpoint: str
    growth_rate_pct: float
    approaching_clouds: List[Dict[str, Any]]
    all_rain_clusters: List[Dict[str, Any]]
    rain_summary: str
    is_outdated: bool
    failover_notice: Optional[str]
    tracking_mode: str
    locked_target_id: Optional[str]
    
    # Bytes for images
    radar_gif_bytes: Optional[bytes]
    radar_hq_gif_bytes: Optional[bytes]
    radar_static_bytes: Optional[bytes]
    radar_tracking_bytes: Optional[bytes]
    rain_timeline_bytes: Optional[bytes]
    radar_multiframe_bytes: Optional[bytes]
    
    tmd_timestamp_utc: str
    tmd_timestamp_bkk: str
