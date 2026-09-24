from app.core.dev_settings import get_dev_settings

import logging
import time
import os
from app.services.tmd_radar.cache_manager import radar_cache
import asyncio
import json
import math
import cv2
import io
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Union
from enum import StrEnum
from PIL import Image, ImageDraw, ImageFont
from zoneinfo import ZoneInfo

class WeatherEndpoint(StrEnum):
    TMD_RADAR = "tmd-radar"
    RAINBOW_LOCAL = "rainbow-local"
    TOMORROW = "tomorrow"
    RAINBOW_GLOBAL = "rainbow-global"
    XWEATHER = "xweather"
    OPEN_METEO = "open-meteo"

    @classmethod
    def priority_order(cls) -> list[str]:
        return [e.value for e in cls]
from .tomorrow import TomorrowService
from .rainbow import RainbowService
from .xweather import XweatherService
from .open_meteo import OpenMeteoService
from .tmd_radar_processor import TMDRadarProcessor
logger = logging.getLogger(__name__)
from app.dependencies import get_repo_context

# ─── Developer Config (runtime-adjustable via /devmock config) ────────────────
# These override the hard-coded defaults in find_approaching_clouds / get_all_rain_clusters.
def log_growth_decay_telemetry(
    target_label: Optional[str],
    dbz_now: float,
    dbz_prev: float,
    growth_rate: float,
    context: str = "general"
) -> None:
    """Logs structured telemetry for cloud cell growth / decay rates."""
    sign = "+" if growth_rate >= 0 else ""
    rate_pct = growth_rate * 100.0
    if rate_pct > 5.0:
        trend = "intensifying"
    elif rate_pct < -5.0:
        trend = "dissipating"
    else:
        trend = "steady"
        
    lbl_str = target_label or "UNKNOWN"
    logger.info(
        f"[GROWTH_DECAY] context={context} target={lbl_str} now={dbz_now:.1f}dBZ prev={dbz_prev:.1f}dBZ "
        f"rate={sign}{rate_pct:.1f}%/15min trend={trend}"
    )


# ─── Parametric Mock Scenario Helpers ────────────────────────────────────────

# Direction abbreviation → compass bearing (degrees, 0=N, 90=E)
_CARDINAL_TO_DEG: Dict[str, float] = {
    "N": 0.0, "NNE": 22.5, "NE": 45.0, "ENE": 67.5,
    "E": 90.0, "ESE": 112.5, "SE": 135.0, "SSE": 157.5,
    "S": 180.0, "SSW": 202.5, "SW": 225.0, "WSW": 247.5,
    "W": 270.0, "WNW": 292.5, "NW": 315.0, "NNW": 337.5,
}


def _parse_scenario_params(params_str: str) -> Dict[str, Any]:
    """
    Parse a /devmock scenario parameter string into a dict.

    Examples
    --------
    "rain_in:20 dbz:40 wind:60 wind_dir:N"  →  {"rain_in": 20, "dbz": 40, "wind": 60, "wind_dir": "N"}
    "rain_stopping:10 dbz:30"               →  {"rain_stopping": 10, "dbz": 30}
    "no_rain wind:45 wind_dir:SE"           →  {"no_rain": True, "wind": 45, "wind_dir": "SE"}
    """
    result: Dict[str, Any] = {}
    for token in params_str.strip().split():
        if ":" in token:
            key, _, raw_val = token.partition(":")
            key = key.strip().lower()
            raw_val = raw_val.strip()
            # Try numeric conversion first
            try:
                result[key] = float(raw_val) if "." in raw_val else int(raw_val)
            except ValueError:
                # loc:name should stay lowercase; direction codes (wind_dir) go uppercase
                result[key] = raw_val if key == "loc" else raw_val.upper()
        else:
            # Flag-style token (e.g. "no_rain")
            result[token.lower()] = True
    return result


def _build_mock_clouds_from_scenario(
    scenario: Dict[str, Any],
    user_px: int,
    user_py: int,
    km_per_pixel: float = 1.5,
) -> list:
    """
    Build a synthetic list of cloud dicts from a parametric scenario.

    The cloud dicts are identical in structure to what
    `TMDRadarProcessor.find_approaching_clouds()` returns, so they
    feed seamlessly into the rest of the prediction pipeline.

    Parameters
    ----------
    scenario : dict from _parse_scenario_params()
    user_px, user_py : pixel coordinate of the user's location
    km_per_pixel : rough scale factor for converting wind_speed → vx/vy
    """
    if scenario.get("no_rain"):
        return []  # Caller will use only wind data

    # ── Resolve dBZ (default 35) ──────────────────────────────────────────
    dbz = float(scenario.get("dbz", 35.0))
    dbz = max(15.0, min(75.0, dbz))

    # ── Resolve wind vector ───────────────────────────────────────────────
    # In image coordinates: vx > 0 = East, vy < 0 = North
    # vx/vy units = pixels per 15 minutes
    wind_kmh = float(scenario.get("wind", 20.0))
    wind_dir_str = str(scenario.get("wind_dir", "N")).upper()
    bearing_deg = _CARDINAL_TO_DEG.get(wind_dir_str, 0.0)  # degrees from North
    bearing_rad = math.radians(bearing_deg)
    # Pixels the cloud travels in 15 minutes
    km_per_15m = wind_kmh / 4.0
    pixels_per_15m = km_per_15m / max(0.01, km_per_pixel)
    vx = pixels_per_15m * math.sin(bearing_rad)   # East component
    vy = -pixels_per_15m * math.cos(bearing_rad)  # North component (image y is inverted)

    growth_rate = float(scenario.get("growth", 0.0))
    num_clusters = int(scenario.get("clusters", 1))
    num_clusters = max(1, min(5, num_clusters))

    clouds = []

    # ── rain_stopping: cloud is currently on top of the user (eta < 0) ───
    if "rain_stopping" in scenario:
        stop_in = float(scenario["rain_stopping"])
        # eta_min < 0 means rain already here; cloud moves away in stop_in mins
        eta = -stop_in
        # Place cloud at user location (it's already overhead)
        cx = user_px
        cy = user_py
        clouds.append({
            "cx": cx, "cy": cy,
            "vx": vx, "vy": vy,
            "dbz_now": dbz, "dbz_prev": max(15.0, dbz - 5.0),
            "predicted_dbz": max(0.0, dbz * ((1 + growth_rate) ** max(0.0, -eta / 15.0))),
            "eta_min": eta,
            "growth_rate": growth_rate,
            "dist": 0.0,
        })
        return clouds

    # ── rain_in: cloud is approaching, will arrive in N minutes ──────────
    base_eta = float(scenario.get("rain_in", scenario.get("eta", 15.0)))
    base_eta = max(0.0, base_eta)

    for i in range(num_clusters):
        # Spread multiple clusters slightly around the arrival time
        eta_offset = i * 10.0
        eta = base_eta + eta_offset

        # Distance from user = speed × time
        dist_px = pixels_per_15m * (eta / 15.0)

        # Cloud is upstream: opposite of its travel direction
        cx = int(user_px - vx * (eta / 15.0))
        cy = int(user_py - vy * (eta / 15.0))

        # Slightly vary dBZ between clusters
        c_dbz = max(15.0, dbz - i * 5.0)
        predicted = max(0.0, min(75.0, c_dbz * ((1 + growth_rate) ** (eta / 15.0))))

        clouds.append({
            "cx": cx, "cy": cy,
            "vx": vx, "vy": vy,
            "dbz_now": c_dbz, "dbz_prev": max(15.0, c_dbz - 3.0),
            "predicted_dbz": predicted,
            "eta_min": eta,
            "growth_rate": growth_rate,
            "dist": dist_px,
        })

    return clouds


# ─── End Parametric Mock Helpers ──────────────────────────────────────────────

_MAX_OCR_CACHE_DRIFT_SEC = 90 * 60  # reject live OCR mis-parses far from polled cache ts


async def _resolve_radar_overlay_utc(
    latest_frame: np.ndarray,
    last_modified_dt: Optional[datetime],
    frame_timestamps: Optional[List[int]] = None,
    *,
    processor: Optional[TMDRadarProcessor] = None,
    frame_source: str = "static_cache",
) -> datetime:
    """
    Pick the UTC timestamp stamped on radar overlays.

    Priority:
    1. Per-frame timestamp from Firestore cache (most accurate for cached frames)
    2. Live OCR on the static 800×800 image
    3. Live OCR on the cached latest frame / timestamp crop
    """
    cache_ts: Optional[int] = None
    if frame_timestamps:
        cache_ts = frame_timestamps[-1]
        logger.info(f"DEBUG_RESOLVE: Using frame_timestamps[-1] = {cache_ts}")
    elif last_modified_dt:
        cache_ts = int(last_modified_dt.timestamp())
        logger.info(f"DEBUG_RESOLVE: Using last_modified_dt = {cache_ts}")

    # Priority 1: Use frame_timestamps from cache (most accurate for the actual frame)
    if cache_ts is not None:
        logger.info(f"DEBUG_RESOLVE: Returning cache timestamp: {datetime.fromtimestamp(cache_ts, timezone.utc)}")
        return datetime.fromtimestamp(cache_ts, timezone.utc)

    ocr_frame = latest_frame
    if processor is not None:
        try:
            static_frame = await processor.decode_static_frame()
            if static_frame is not None:
                ocr_frame = static_frame
        except Exception as e:
            logger.warning(f"Static image decode for overlay timestamp failed: {e}")

    parsed_ts: Optional[int] = None
    try:
        from app.services.ocr_service import OCRService
        ocr_svc = OCRService()
        parsed_ts = await ocr_svc.extract_parsed_timestamp(
            ocr_frame, skip_hash_cache=True, use_crop=True,
        )
        if parsed_ts is None and ocr_frame is not latest_frame:
            parsed_ts = await ocr_svc.extract_parsed_timestamp(
                latest_frame, skip_hash_cache=True, use_crop=True,
            )
        logger.info(f"DEBUG_RESOLVE: OCR parsed_ts = {parsed_ts}")
    except Exception as e:
        logger.warning(f"Failed to OCR frame timestamp: {e}")

    if parsed_ts is not None:
        if cache_ts is None or abs(parsed_ts - cache_ts) <= _MAX_OCR_CACHE_DRIFT_SEC:
            logger.info(f"DEBUG_RESOLVE: Using OCR timestamp: {datetime.fromtimestamp(parsed_ts, timezone.utc)}")
            return datetime.fromtimestamp(parsed_ts, timezone.utc)
        logger.warning(
            "OCR timestamp drifted %.0fm from cache; keeping cache value",
            abs(parsed_ts - cache_ts) / 60.0,
        )

    if last_modified_dt is not None:
        logger.info(f"DEBUG_RESOLVE: Using last_modified_dt fallback: {last_modified_dt}")
        return last_modified_dt
    if cache_ts is not None:
        logger.info(f"DEBUG_RESOLVE: Using cache_ts fallback: {datetime.fromtimestamp(cache_ts, timezone.utc)}")
        return datetime.fromtimestamp(cache_ts, timezone.utc)
    logger.warning(f"DEBUG_RESOLVE: No timestamp available, using current time: {datetime.now(timezone.utc)}")
    return datetime.now(timezone.utc)


_GLOBAL_TMD_CACHE = {}
_GLOBAL_TMD_LOCKS = {
    "kkn120": asyncio.Lock(),
    "kkn240": asyncio.Lock(),
    "skn240": asyncio.Lock(),
}


def invalidate_station_memory_cache(station_code: str) -> None:
    """Evict a station from the in-process TMD frame cache.
    Call this whenever crop calibration values are updated in DB so that
    the next bot request forces a fresh Firestore / live download."""
    if radar_cache.get(station_code) is not None:
        radar_cache.invalidate(station_code)
        logger.info(f"[CACHE INVALIDATE] In-memory cache cleared for station={station_code}")

class WeatherManager:
    LAST_USED_STATION: dict[int, str] = {}

    def __init__(self):
        self.xweather_svc = XweatherService()
        self.tomorrow_svc = TomorrowService()
        self.rainbow_svc = RainbowService()
        self.open_meteo_svc = OpenMeteoService()

    async def predict_rain(
        self,
        lat: float,
        lng: float,
        mock_state: Optional[str] = None,
        force_endpoint: Optional[str] = None,
        chat_id: Optional[Union[str, int]] = None,
        message_id_to_edit: Optional[Union[str, int]] = None,
        show_labels: bool = True,
        location_name: Optional[str] = None,
    ) -> dict:
        """
        ดึงข้อมูลพยากรณ์ฝนโดยผ่านระบบ Fallback อัตโนมัติ:
        หรือบังคับ API ตาม force_endpoint
        """
        if mock_state == "error":
            return {"endpoint": "error", "error": "Simulated error from /devmock error"}

        service_map = {
            "xweather": lambda: self.xweather_svc.predict_rain_by_location(lat, lng, mock_state=mock_state),
            "tomorrow": lambda: self.tomorrow_svc.predict_rain_by_location(lat, lng, mock_state=mock_state),
            "rainbow-local": lambda: self.rainbow_svc.predict_rain_by_location(lat, lng, endpoint_type="local", mock_state=mock_state),
            "rainbow-global": lambda: self.rainbow_svc.predict_rain_by_location(lat, lng, endpoint_type="global", mock_state=mock_state),
            "open-meteo": lambda: self.open_meteo_svc.predict_rain_by_location(lat, lng, mock_state=mock_state),
            "tmd-radar": lambda: self._get_tmd_prediction(lat, lng, mock_state=mock_state, location_name=location_name, chat_id=chat_id, message_id_to_edit=message_id_to_edit, show_labels=show_labels),
            "kkn120": lambda: self._get_tmd_prediction(lat, lng, force_station="kkn120", mock_state=mock_state, location_name=location_name, chat_id=chat_id, message_id_to_edit=message_id_to_edit, show_labels=show_labels),
            "kkn240": lambda: self._get_tmd_prediction(lat, lng, force_station="kkn240", mock_state=mock_state, location_name=location_name, chat_id=chat_id, message_id_to_edit=message_id_to_edit, show_labels=show_labels),
            "skn240": lambda: self._get_tmd_prediction(lat, lng, force_station="skn240", mock_state=mock_state, location_name=location_name, chat_id=chat_id, message_id_to_edit=message_id_to_edit, show_labels=show_labels)
        }


        # --- โหมดบังคับ endpoint (ไม่ผ่าน fallback) ---
        if force_endpoint and force_endpoint in service_map:
            try:
                result = await service_map[force_endpoint]()
                result["endpoint"] = force_endpoint
                logger.info(f"Successfully fetched weather from {force_endpoint} [forced]")
                return result
            except Exception as e:
                logger.error(f"{force_endpoint} failed (forced mode): {e}")
                return {
                    "predictions": [],
                    "intensity": "ไม่ทราบ",
                    "max_rain": 0.0,
                    "duration_minutes": 0,
                    "wind_speed_kmh": 0.0,
                    "endpoint": "error",
                }

        # --- โหมดปกติ: Auto-select based on accuracy score ---
        async with get_repo_context() as repo:
            reliabilities = await repo.get_all_api_reliability()
            
        priority_order = WeatherEndpoint.priority_order()
        
        def sort_key(k):
            score = reliabilities.get(k, 0.0)
            idx = priority_order.index(k) if k in priority_order else 999
            return (score, -idx)

        sorted_endpoints = sorted(reliabilities.keys(), key=sort_key, reverse=True)
        
        for ep in sorted_endpoints:
            if ep not in service_map:
                continue
                
            try:
                result = await service_map[ep]()
                logger.info(f"Successfully fetched weather from {ep} (accuracy: {reliabilities[ep]:.2f})")
                if "endpoint" not in result:
                    result["endpoint"] = ep
                    
                # หากดึงสำเร็จและมีการทายว่าฝนจะตก ให้บวก total_queries
                if result.get("max_rain", 0.0) > 0:
                    async with get_repo_context() as update_repo:
                        await update_repo.record_api_query_success(ep)
                        
                return result
            except Exception as e:
                logger.warning(f"{ep} failed: {e}. Falling back to next...")
                
        logger.error("All weather APIs failed in auto-select.")
        return {
            "predictions": [],
            "intensity": "ไม่ทราบ",
            "max_rain": 0.0,
            "duration_minutes": 0,
            "wind_speed_kmh": 0.0,
            "endpoint": "error",
        }

    async def compare_all_apis(self, lat: float, lng: float, mock_state: Optional[str] = None, location_name: Optional[str] = None) -> dict:
        """
        เรียก 3 API พร้อมกันเพื่อเปรียบเทียบผลลัพธ์
        """
        
        async with get_repo_context() as repo:
            reliabilities = await repo.get_all_api_reliability()
        
        async def safe_call(name, coro):
            try:
                res = await coro
                res["endpoint"] = name
                res["accuracy_score"] = reliabilities.get(name, 0.0)
                return name, res
            except Exception as e:
                import re
                error_msg = str(e) if str(e) else repr(e)
                error_msg = re.sub(r'client_id=[^&\s]+', 'client_id=***', error_msg)
                error_msg = re.sub(r'client_secret=[^&\s]+', 'client_secret=***', error_msg)
                
                if "401" in error_msg:
                    error_msg = "แหล่งข้อมูลปิดปรับปรุงหรือสิทธิ์การเข้าถึงมีปัญหาชั่วคราว"
                elif "429" in error_msg:
                    error_msg = "ดึงข้อมูลถี่เกินไปชั่วคราว กรุณาเว้นระยะแล้วลองใหม่อีกครั้ง"
                elif "timeout" in error_msg.lower():
                    error_msg = "การเชื่อมต่อขัดข้องหรือสัญญาณขาดหายชั่วคราว"
                elif "403" in error_msg:
                    error_msg = "แหล่งข้อมูลปฏิเสธการเชื่อมต่อชั่วคราว"
                elif "50" in error_msg:
                    error_msg = "ระบบเซิร์ฟเวอร์ของผู้ให้บริการขัดข้องชั่วคราว"
                    
                logger.error(f"Error fetching from {name}: {error_msg}")
                return name, {"error": error_msg, "endpoint": name, "max_rain": 0.0, "accuracy_score": reliabilities.get(name, 0.0)}

        async def fetch_xweather_full():
            res_rain, res_alerts = await asyncio.gather(
                self.xweather_svc.predict_rain_by_location(lat, lng, mock_state=mock_state),
                self.get_advanced_alerts(lat, lng, mock_state=mock_state)
            )
            storm = res_alerts.get("stormcell")
            if storm and storm.get("distance_km") is not None:
                res_rain["storm_distance_km"] = storm["distance_km"]
            return res_rain

        tasks = [
            safe_call("xweather", fetch_xweather_full()),
            safe_call("tomorrow", self.tomorrow_svc.predict_rain_by_location(lat, lng, mock_state=mock_state)),
            safe_call("rainbow-local", self.rainbow_svc.predict_rain_by_location(lat, lng, endpoint_type="local", mock_state=mock_state)),
            safe_call("rainbow-global", self.rainbow_svc.predict_rain_by_location(lat, lng, endpoint_type="global", mock_state=mock_state)),
            safe_call("open-meteo", self.open_meteo_svc.predict_rain_by_location(lat, lng, mock_state=mock_state)),
            safe_call("tmd-radar", self._get_tmd_prediction(lat, lng, mock_state=mock_state, location_name=location_name))
        ]
        
        results = await asyncio.gather(*tasks)
        
        final_results = {}
        for k, v in results:
            if "predictions" in v:
                v["predictions"] = v["predictions"][:15]
            # Strip binary bytes from comparison result to prevent JSON encoding errors
            for byte_field in [
                "radar_static_bytes", 
                "radar_tracking_bytes", 
                "rain_timeline_bytes", 
                "radar_multiframe_bytes", 
                "radar_gif_bytes", 
                "radar_hq_gif_bytes"
            ]:
                if byte_field in v:
                    v[byte_field] = None
            final_results[k] = v
            
        return final_results

    async def get_advanced_alerts(self, lat: float, lng: float, mock_state: Optional[str] = None) -> dict:
        """
        ดึงข้อมูลเตือนภัยขั้นสูงจาก Xweather (Advisories, Lightning, Stormcells)
        ถ้า Xweather ปิดอยู่ หรือ API พัง จะพยายามดึงข้อมูลลมจาก Open-Meteo แทน (Contingency)
        """
        try:
            if not self.xweather_svc.enabled or self.xweather_svc._is_circuit_open():
                raise Exception("Xweather is disabled or circuit is open")
            return await self.xweather_svc.get_advanced_alerts(lat, lng, mock_state=mock_state)
        except Exception as e:
            logger.warning(f"Failed to fetch advanced alerts from Xweather: {e}. Falling back to Open-Meteo for wind vectors.")
            try:
                wind_data = await self.open_meteo_svc.get_wind_vector(lat, lng, mock_state=mock_state)
                return {
                    "advisories": [], 
                    "lightning": None, 
                    "stormcell": {
                        "distance_km": None,
                        "direction": wind_data.get("direction_cardinal", ""),
                        "speed_kmh": wind_data.get("speed_kmh", 0),
                        "max_dbz": None
                    }
                }
            except Exception as e_meteo:
                logger.error(f"Open-Meteo Contingency failed: {e_meteo}")
                return {"advisories": [], "lightning": None, "stormcell": None}

    async def load_persistent_cache_to_memory(self, station_code: str, processor) -> Optional[tuple]:
        """
        Loads the radar cache from Firestore, populates _GLOBAL_TMD_CACHE, 
        and returns the cached data tuple. Returns None if it fails or has no cache.
        """
        # Check if we should override with local fixture files for testing
        import sys
        is_testing = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ
        is_local_fixtures_mode = (
            os.getenv("USE_LOCAL_FIXTURES", "false").lower() == "true" or
            get_dev_settings().use_local_fixtures
        )
        if is_local_fixtures_mode and not is_testing:
            fixture_name = f"test_{station_code}_frames.npz"
            fixture_path = os.path.join(os.path.dirname(__file__), "..", "tests", fixture_name)
            if not os.path.exists(fixture_path):
                fixture_path = os.path.join(os.path.dirname(__file__), "..", "..", "tests", fixture_name)
            
            if os.path.exists(fixture_path):
                import numpy as np
                import time
                from datetime import datetime, timezone
                import cv2
                
                logger.info(f"🛠️ [LOCAL FIXTURE MODE] Loading fixture from {fixture_path}...")
                data = np.load(fixture_path, allow_pickle=True)
                frame_arr = data["frames"]
                frames = [cv2.cvtColor(np.array(frame_arr[i]), cv2.COLOR_BGR2RGB) for i in range(frame_arr.shape[0])]
                flow = np.array(data["flow"])
                meta = dict(data.get("meta", {}).item()) if "meta" in data else {}
                frame_timestamps = meta.get("frame_timestamps", [])
                frame_urls = meta.get("frame_urls", [])
                
                last_modified_dt = datetime.fromtimestamp(frame_timestamps[-1], timezone.utc) if frame_timestamps else datetime.now(timezone.utc)
                data_gap_minutes = 15.0
                if len(frame_timestamps) >= 2:
                    data_gap_minutes = (frame_timestamps[-1] - frame_timestamps[-2]) / 60.0
                
                is_loop = frames[-1].shape[0] < 600 or frames[-1].shape[1] < 600
                frame_source = "loop_gif" if is_loop else "static_cache"
                
                radar_cache.set(station_code, frames, last_modified_dt, flow, frame_source, data_gap_minutes, frame_timestamps, frame_urls)
                logger.info(f"🛠️ [LOCAL FIXTURE MODE] Successfully loaded {len(frames)} frames from local fixture.")
                return radar_cache.get(station_code)

        # Check if we should override with backup files for testing
        is_backup_mode = (
            os.getenv("USE_SKN240_BACKUP", "false").lower() == "true" or
            get_dev_settings().use_skn240_backup
        )
        if station_code == "skn240" and is_backup_mode:
            bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "fonmayang.firebasestorage.app")
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            
            logger.info("🛠️ [SKN240 BACKUP MODE] Listing blobs in radar/skn240_backup/...")
            try:
                blobs = list(bucket.list_blobs(prefix="radar/skn240_backup/"))
                backup_frames = []
                for b in blobs:
                    # e.g., radar/skn240_backup/skn240_1784212828.gif
                    base_name = b.name.split("/")[-1]
                    ts_str = base_name.replace("skn240_", "").replace(".gif", "")
                    try:
                        ts = int(ts_str)
                        backup_frames.append({"url": b.name, "timestamp": ts})
                    except ValueError:
                        continue
                
                if backup_frames:
                    backup_frames = sorted(backup_frames, key=lambda x: x["timestamp"])
                    # Shift timestamps so the latest one matches the current time
                    import time
                    now_ts = int(time.time())
                    original_latest_ts = backup_frames[-1]["timestamp"]
                    for f in backup_frames:
                        delta = original_latest_ts - f["timestamp"]
                        f["timestamp"] = now_ts - delta
                    
                    cache = {"frames": backup_frames}
                    logger.info(f"🛠️ [SKN240 BACKUP MODE] Successfully loaded {len(backup_frames)} frames from backup folder.")
                else:
                    logger.warning("🛠️ [SKN240 BACKUP MODE] No files found in radar/skn240_backup/! Falling back to DB cache.")
                    async with get_repo_context() as repo:
                        cache = await repo.get_latest_radar_cache(station_code)
            except Exception as e_backup:
                logger.error(f"🛠️ [SKN240 BACKUP MODE] Error loading backup files: {e_backup}. Falling back to DB cache.")
                async with get_repo_context() as repo:
                    cache = await repo.get_latest_radar_cache(station_code)
        else:
            async with get_repo_context() as repo:
                cache = await repo.get_latest_radar_cache(station_code)
        
        if not cache or not (cache.get("frames") or (cache.get("url_t") and cache.get("url_t_minus_1"))):
            return None

        bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "fonmayang.firebasestorage.app")
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        cache_frames = cache.get("frames")
        if not cache_frames:
            cache_frames = [
                {"url": cache.get("url_t"), "timestamp": cache.get("timestamp")},
                {"url": cache.get("url_t_minus_1"), "timestamp": cache.get("timestamp") - 900}
            ]
            
        cache_frames = sorted(cache_frames, key=lambda x: x["timestamp"])
        
        async def fetch_blob(f_data):
            blob = bucket.blob(f_data["url"])
            try:
                img_bytes = await asyncio.to_thread(blob.download_as_bytes)
                return img_bytes, f_data["timestamp"]
            except Exception as e:
                logger.warning(f"Failed to download cached frame {f_data['url']}: {e}")
                return None, None
                
        results = await asyncio.gather(*[fetch_blob(f) for f in cache_frames])
        valid_frames_data = [res for res in results if res[0] is not None]
        valid_frames_data.sort(key=lambda x: x[1])
        
        if len(valid_frames_data) < 2:
            return None

        decoded_frames = []
        target_shape = None
        import cv2
        import numpy as np
        from datetime import datetime, timezone
        for f_bytes, ts in valid_frames_data[-6:]:
            t_np = np.frombuffer(f_bytes, np.uint8)
            frame = cv2.imdecode(t_np, cv2.IMREAD_COLOR)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if target_shape is None:
                target_shape = frame.shape[:2]
            elif frame.shape[:2] != target_shape:
                frame = cv2.resize(frame, (target_shape[1], target_shape[0]), interpolation=cv2.INTER_NEAREST)
            decoded_frames.append(frame)
            
        frames = decoded_frames
        frame_timestamps = [ts for _, ts in valid_frames_data[-6:]]
        last_modified_dt = datetime.fromtimestamp(frame_timestamps[-1], timezone.utc)
        
        if get_dev_settings().flow_mode == "average":
            flow = processor.calculate_average_optical_flow(frames)
        else:
            flow = processor.calculate_optical_flow(frames)
        
        data_gap_minutes = (frame_timestamps[-1] - frame_timestamps[-2]) / 60.0
        if data_gap_minutes > 16.0:
            # Normalize flow to represent exactly 15 minutes of displacement
            flow = flow / (data_gap_minutes / 15.0)
            
        is_loop = frames[-1].shape[0] <= 1000 or frames[-1].shape[1] <= 1000
        frame_source = "loop_gif" if is_loop else "static_cache"
        logger.info(
            f"[{station_code}] 🗃️  Firestore cache LOADED — "
            f"{len(frames)} frames, source={frame_source}, "
            f"latest_ts={frame_timestamps[-1] if frame_timestamps else 'n/a'}"
        )
        
        import time
        # Collect frame URLs from the Firestore cache (for reproducibility)
        frame_urls = [f["url"] for f in cache_frames[-6:]] if cache_frames else []
        radar_cache.set(station_code, frames, last_modified_dt, flow, frame_source, data_gap_minutes, frame_timestamps, frame_urls)
        return radar_cache.get(station_code)

    async def _get_tmd_prediction(self, lat: float, lng: float, force_station: Optional[str] = None, **kwargs) -> Optional[Dict[str, Any]]:
        from app.services.tmd_radar.adapter import TMDNowcastAdapter
        adapter = TMDNowcastAdapter(self)
        result = await adapter.predict(lat, lng, force_station, **kwargs)
        return result.model_dump() if result else None
