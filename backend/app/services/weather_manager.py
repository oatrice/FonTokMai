import logging
import time
import os
import asyncio
import json
import math
import cv2
import io
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from PIL import Image, ImageDraw, ImageFont
from zoneinfo import ZoneInfo
from .tomorrow import TomorrowService
from .rainbow import RainbowService
from .xweather import XweatherService
from .open_meteo import OpenMeteoService
from .tmd_radar_processor import TMDRadarProcessor
logger = logging.getLogger(__name__)
from app.dependencies import get_repo_context

# ─── Developer Config (runtime-adjustable via /devmock config) ────────────────
# These override the hard-coded defaults in find_approaching_clouds / get_all_rain_clusters.
_DEV_CONFIG: dict = {
    "cluster_min":    3,      # min pixels to form a valid cloud cluster
    "search_radius":  80,     # px radius to scan for approaching clouds
    "min_dbz":        10.0,   # minimum dBZ to count as rain
    "dot_threshold":  0.5,    # dot product threshold (how directly it must approach)
    "flow_mode":      "average", # 'latest' or 'average'
    "hit_radius":     8,      # radius around user to check for rain hits
    "verbose":        False,  # Enable verbose debugging logs
}


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

class WeatherManager:
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
            "tmd-radar": lambda: self._get_tmd_prediction(lat, lng, mock_state=mock_state),
            "kkn120": lambda: self._get_tmd_prediction(lat, lng, force_station="kkn120", mock_state=mock_state),
            "kkn240": lambda: self._get_tmd_prediction(lat, lng, force_station="kkn240", mock_state=mock_state),
            "skn240": lambda: self._get_tmd_prediction(lat, lng, force_station="skn240", mock_state=mock_state)
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
            
        sorted_endpoints = sorted(reliabilities.keys(), key=lambda k: reliabilities[k], reverse=True)
        
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

    async def compare_all_apis(self, lat: float, lng: float, mock_state: Optional[str] = None) -> dict:
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
            safe_call("tmd-radar", self._get_tmd_prediction(lat, lng, mock_state=mock_state))
        ]
        
        results = await asyncio.gather(*tasks)
        
        final_results = {}
        for k, v in results:
            if "predictions" in v:
                v["predictions"] = v["predictions"][:15]
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
        
        if _DEV_CONFIG.get("flow_mode", "latest") == "average":
            flow = processor.calculate_average_optical_flow(frames)
        else:
            flow = processor.calculate_optical_flow(frames)
        
        data_gap_minutes = (frame_timestamps[-1] - frame_timestamps[-2]) / 60.0
        if data_gap_minutes > 16.0:
            # Normalize flow to represent exactly 15 minutes of displacement
            flow = flow / (data_gap_minutes / 15.0)
            
        is_loop = frames[-1].shape[0] < 800 or frames[-1].shape[1] < 800
        frame_source = "loop_gif" if is_loop else "static_cache"
        logger.info(
            f"[{station_code}] 🗃️  Firestore cache LOADED — "
            f"{len(frames)} frames, source={frame_source}, "
            f"latest_ts={frame_timestamps[-1] if frame_timestamps else 'n/a'}"
        )
        
        import time
        _GLOBAL_TMD_CACHE[station_code] = (
            frames, last_modified_dt, time.time(), flow,
            frame_source, data_gap_minutes, frame_timestamps,
        )
        return _GLOBAL_TMD_CACHE[station_code]

    async def _get_tmd_prediction(self, lat: float, lng: float, force_station: Optional[str] = None, mock_state: Optional[str] = None) -> dict:
        """
        Wrapper for TMD Radar predictions using Optical Flow Nowcasting.
        Uses dot-product approach vector filter to find approaching cloud clusters,
        then ranks by ETA and generates a smart summary with growth/decay rates.
        """
        
        if force_station:
            stations_to_check = [force_station]
        else:
            from app.services.tmd_radar_config import STATIONS
            stations = ["kkn120", "kkn240", "skn240"]
            
            def get_dist(code):
                conf = STATIONS.get(code)
                if not conf: return float('inf')
                # Simple euclidean distance for sorting priority
                import math
                return math.hypot(lat - conf.center_lat, lng - conf.center_lng)
                
            stations_to_check = sorted(stations, key=get_dist)

        for station_code in stations_to_check:
            try:
                processor = TMDRadarProcessor(station_code)
                px, py = processor.latlng_to_pixel(lat, lng, is_loop=False)
                if px is None or py is None:
                    continue

                # Use module-level cache and lock to prevent cache stampede
                lock = _GLOBAL_TMD_LOCKS.get(station_code)
                if lock is None:
                    continue
                
                async with lock:
                    cached_data = _GLOBAL_TMD_CACHE.get(station_code)

                    if cached_data and (time.time() - cached_data[2]) < 600:
                        frames, last_modified_dt, flow = cached_data[0], cached_data[1], cached_data[3]
                        frame_source = cached_data[4] if len(cached_data) > 4 else "static_cache"
                        data_gap_minutes = cached_data[5] if len(cached_data) > 5 else 15.0
                        frame_timestamps = list(cached_data[6]) if len(cached_data) > 6 else []
                        age_s = int(time.time() - cached_data[2])
                        logger.info(
                            f"[{station_code}] 📦 IN-MEMORY cache HIT — "
                            f"{len(frames)} frames, source={frame_source}, age={age_s}s"
                        )
                    else:
                        cached_data = await self.load_persistent_cache_to_memory(station_code, processor)
                        if cached_data:
                            frames, last_modified_dt, flow = cached_data[0], cached_data[1], cached_data[3]
                            frame_source = cached_data[4]
                            data_gap_minutes = cached_data[5]
                            frame_timestamps = list(cached_data[6])
                        else:
                            frames = []
                            last_modified_dt = None
                            flow = None
                            frame_source = "static_cache"
                            frame_timestamps = []
                            data_gap_minutes = 15.0
                        if not frames or len(frames) < 2:
                            fresh_frames, fresh_dt, fresh_loop_bytes = await processor.fetch_loop_gif_and_extract_frames()
                            if len(fresh_frames) >= 2:
                                frames = fresh_frames[-6:]
                                target_shape = frames[-1].shape[:2]
                                for i in range(len(frames)-1):
                                    if frames[i].shape[:2] != target_shape:
                                        frames[i] = cv2.resize(frames[i], (target_shape[1], target_shape[0]), interpolation=cv2.INTER_NEAREST)
                                last_modified_dt = fresh_dt or datetime.now(timezone.utc)
                                if fresh_dt:
                                    latest_ts = int(fresh_dt.timestamp())
                                    frame_timestamps = [
                                        latest_ts - (len(frames) - 1 - i) * 900
                                        for i in range(len(frames))
                                    ]
                                else:
                                    frame_timestamps = []
                                if _DEV_CONFIG.get("flow_mode", "latest") == "average":
                                    flow = processor.calculate_average_optical_flow(frames)
                                else:
                                    flow = processor.calculate_optical_flow(frames)
                                data_gap_minutes = 15.0 # Loop GIFs are assumed to be exactly 15m apart
                                frame_source = "loop_gif"
                                logger.warning(
                                    f"[{station_code}] 🌀 LIVE loop GIF fallback — "
                                    f"{len(frames)} frames fetched direct from TMD (Firestore cache was empty/stale)"
                                )
                                _GLOBAL_TMD_CACHE[station_code] = (
                                    frames, last_modified_dt, time.time(), flow,
                                    frame_source, data_gap_minutes, frame_timestamps,
                                )
                                # Also persist to Firestore so next call after in-memory expiry
                                # uses Firestore instead of re-fetching loop GIF again.
                                try:
                                    saved_frames = []
                                    for f_img, f_ts in zip(frames, frame_timestamps):
                                        # Resize to 800×800 so is_loop detection (frame.shape < 800)
                                        # returns False when reloaded — ensuring static pixel coords.
                                        if f_img.shape[0] != 800 or f_img.shape[1] != 800:
                                            f_img = cv2.resize(f_img, (800, 800), interpolation=cv2.INTER_NEAREST)
                                        is_ok, buf = cv2.imencode(".png", cv2.cvtColor(f_img, cv2.COLOR_RGB2BGR))
                                        if is_ok:
                                            f_url = await processor.save_polled_frame(buf.tobytes())
                                            saved_frames.append({"url": f_url, "timestamp": f_ts})

                                    if saved_frames:
                                        async with get_repo_context() as _repo:
                                            await _repo.set_latest_radar_cache(
                                                station_code=station_code,
                                                frames=saved_frames,
                                            )
                                        logger.info(
                                            f"[{station_code}] 🌀 GIF fallback: persisted "
                                            f"{len(saved_frames)} frames to Firestore"
                                        )
                                except Exception as _e:
                                    logger.warning(f"[{station_code}] 🌀 GIF fallback: Firestore persist failed: {_e}")
                            else:
                                continue


                if not frames or len(frames) < 2:
                    continue

                curr_frame = frames[-1].copy()
                prev_frame = frames[-2].copy()

                now_utc = await _resolve_radar_overlay_utc(
                    frames[-1],
                    last_modified_dt,
                    frame_timestamps,
                    processor=processor,
                    frame_source=frame_source,
                )
                logger.info(f"DEBUG_NOW_UTC: station={station_code}, now_utc={now_utc}, frame_timestamps={frame_timestamps}")

                use_loop_mapping = frame_source == "loop_gif"
                user_px, user_py = processor.latlng_to_pixel(lat, lng, is_loop=use_loop_mapping)
                px, py = user_px, user_py
                import logging
                logging.info(f"DEBUG_LOCATION: lat={lat}, lng={lng} -> user_px={user_px}, user_py={user_py} (station: {station_code}, is_loop={use_loop_mapping})")
                if user_px is None or user_py is None:
                    continue

                # Find all cloud clusters approaching the user (using dev-configurable thresholds)
                _cfg = _DEV_CONFIG
                clouds = processor.find_approaching_clouds(
                    curr_frame, prev_frame, flow, user_px, user_py,
                    search_radius=_cfg.get("search_radius", 80),
                    min_dbz=_cfg.get("min_dbz", 10.0),
                    cluster_dist=20,
                    hit_radius=_cfg.get("hit_radius", 20),
                    cluster_min=_cfg.get("cluster_min", 3),
                    dot_threshold=_cfg.get("dot_threshold", 0.5),
                )
                # Also collect ALL rain clusters (any direction) for the always-visible overlay
                all_rain_clusters = await asyncio.to_thread(
                    processor.get_all_rain_clusters,
                    curr_frame, flow, user_px, user_py,
                    scan_radius=min(200, _cfg.get("search_radius", 80) * 2),
                    min_dbz=0.1,  # Lower threshold so even light rain gets clustered and labeled
                    cluster_dist=25,
                )
                
                # Label all_rain_clusters FIRST
                if all_rain_clusters:
                    for i, c in enumerate(all_rain_clusters):
                        # Use A-Z, then AA-ZZ if needed (though usually < 26)
                        c["label"] = chr(ord('A') + min(i, 25))
                        
                # Match labels from all_rain_clusters to clouds
                if all_rain_clusters and clouds:
                    unique_clouds = {}
                    for appr_c in clouds:
                        matched_label = "?"
                        min_d = 9999
                        matched_amb = None
                        for amb_c in all_rain_clusters:
                            d = math.hypot(appr_c["cx"] - amb_c["cx"], appr_c["cy"] - amb_c["cy"])
                            if d < 150 and d < min_d:
                                min_d = d
                                matched_label = amb_c.get("label", "?")
                                matched_amb = amb_c
                                
                        appr_c["label"] = matched_label
                        if matched_amb:
                            appr_c["cx"] = matched_amb["cx"]
                            appr_c["cy"] = matched_amb["cy"]
                            if "pixels" in matched_amb:
                                appr_c["pixels"] = matched_amb["pixels"]
                                
                        # Deduplicate: keep the one with smaller absolute eta (closer to impact or current)
                        label = appr_c["label"]
                        if label not in unique_clouds:
                            unique_clouds[label] = appr_c
                        else:
                            existing = unique_clouds[label]
                            if abs(appr_c.get("eta_min", 9999)) < abs(existing.get("eta_min", 9999)):
                                unique_clouds[label] = appr_c
                    clouds = list(unique_clouds.values())

                # ── Parametric scenario mock (JSON mock_state) ────────────────────
                if mock_state and mock_state.startswith("{"):
                    try:
                        scenario = json.loads(mock_state)
                        # Override clouds completely with synthetic data
                        # Estimate km_per_pixel from station config
                        lon_diff = processor.config.bbox.lng_max - processor.config.bbox.lng_min
                        width_km = lon_diff * 111.0
                        est_km_per_pixel = width_km / max(1, processor.config.loop_crop_width)
                        clouds = _build_mock_clouds_from_scenario(
                            scenario, user_px, user_py, km_per_pixel=est_km_per_pixel
                        )
                    except Exception as e:
                        logger.warning(f"Failed to parse JSON mock_state scenario: {e}")

                # Apply mock overrides
                elif mock_state in ("rain", "storm"):
                    if mock_state == "storm" or not clouds:
                        if mock_state == "storm":
                            clouds = []  # Forcefully clear real clouds to ensure mock storm always shows
                        mock_configs = []
                        if mock_state == "storm":
                            import random
                            intensities = [
                                ((0, 128, 0), 25.0),    # Green exact
                                ((255, 255, 0), 35.0),  # Yellow exact
                                ((255, 128, 0), 45.0),  # Orange exact
                                ((128, 0, 0), 55.0),    # Dark Red exact
                                ((255, 0, 255), 65.0),  # Magenta/Purple exact
                            ]
                            random.shuffle(intensities)
                            bands = [
                                {"color": intensities[0][0], "dbz": intensities[0][1], "base_offset": (-5, 5),   "eta": 0},
                                {"color": intensities[1][0], "dbz": intensities[1][1], "base_offset": (-20, 20), "eta": 5},
                                {"color": intensities[2][0], "dbz": intensities[2][1], "base_offset": (-35, 35), "eta": 10},
                                {"color": intensities[3][0], "dbz": intensities[3][1], "base_offset": (-50, 50), "eta": 15},
                                {"color": intensities[4][0], "dbz": intensities[4][1], "base_offset": (-65, 65), "eta": 20},
                            ]
                        else:
                            # Incoming rain scenario: storm is further away, warning in advance
                            bands = [
                                {"color": (46, 204, 113),  "dbz": 25.0, "base_offset": (-25, 25), "eta": 30},  # Green
                                {"color": (241, 196, 15),  "dbz": 35.0, "base_offset": (-35, 35), "eta": 45},  # Yellow
                            ]
                            
                        for band in bands:
                            bx, by = band["base_offset"]
                            for spread in [-60, -30, 0, 30, 60]:
                                mock_configs.append({
                                    "color": band["color"],
                                    "dbz": band["dbz"],
                                    "offset": (bx + spread, by + spread),
                                    "eta": band["eta"]
                                })

                        for mc in mock_configs:
                            cx, cy = user_px + mc["offset"][0], user_py + mc["offset"][1]
                            vx, vy = (5.0, -5.0) if mock_state == "rain" else (3.0, -3.0)  # Move towards NE
                            clouds.append({
                                "cx": cx, "cy": cy,
                                "vx": vx, "vy": vy,
                                "dbz_now": mc["dbz"], "dbz_prev": mc["dbz"] - 2.0,
                                "predicted_dbz": mc["dbz"],
                                "eta_min": mc["eta"],
                                "growth_rate": 0.05,
                                "dist": max(1, abs(mc["offset"][0]))
                            })
                            
                            if mock_state == "storm":
                                cv2.circle(curr_frame, (cx, cy), 22, mc["color"], -1)
                    else:
                        for c in clouds:
                            c["dbz_now"]       = max(c["dbz_now"], 40.0)
                            c["predicted_dbz"] = max(c["predicted_dbz"], 40.0)
                elif mock_state == "clear":
                    clouds = []

                current_utc = datetime.now(timezone.utc)
                time_offset_min = (current_utc - now_utc).total_seconds() / 60.0
                data_age_minutes = time_offset_min
                
                confidence_score = 1.0
                # Using data_gap_minutes which was computed earlier (defaults to 15.0 if not bound)
                try:
                    gap_min = data_gap_minutes
                except NameError:
                    gap_min = 15.0
                    
                if gap_min > 20 or data_age_minutes > 30:
                    confidence_score = 0.5


                def dbz_to_intensity(d: float) -> str:
                    if d >= 55: return "ฝนตกหนักมาก"
                    if d >= 35: return "ฝนตกหนัก"
                    if d >= 20: return "ฝนตกปานกลาง"
                    if d > 0:   return "ฝนตกเล็กน้อย"
                    return "ไม่มีฝน"

                predictions = []
                max_dbz = 0.0
                current_dbz = processor.get_dbz_at_pixel(curr_frame, px, py)
                
                fallback_vx, fallback_vy = 0.0, 0.0
                if clouds:
                    closest_c = min(clouds, key=lambda c: c.get("dist", 9999))
                    fallback_vx = closest_c.get("vx", 0.0)
                    fallback_vy = closest_c.get("vy", 0.0)
                
                for steps in range(7):
                    offset_min = steps * 15
                    dbz, src_x, src_y = processor.extrapolate_rain_at_pixel(
                        curr_frame, flow, px, py, steps=steps, radius=_cfg.get("hit_radius", 8),
                        fallback_vx=fallback_vx, fallback_vy=fallback_vy
                    )
                    
                    cluster_label = None
                    if dbz >= 10.0 and all_rain_clusters:
                        min_dist = 9999
                        for c in all_rain_clusters:
                            dx = max(c.get("xmin", c["cx"]) - src_x, 0, src_x - c.get("xmax", c["cx"]))
                            dy = max(c.get("ymin", c["cy"]) - src_y, 0, src_y - c.get("ymax", c["cy"]))
                            d = math.hypot(dx, dy)
                            if d <= 20 and d < min_dist:
                                min_dist = d
                                cluster_label = c.get("label")
                                    
                    if mock_state == "rain":
                        dbz = max(dbz, 40.0)
                    elif mock_state == "clear":
                        dbz = 0.0
                        
                    if dbz > max_dbz:
                        max_dbz = dbz
                    
                    pred_time  = current_utc + timedelta(minutes=steps * 15)
                    z_value    = 10 ** (dbz / 10.0)
                    rain_mmhr  = (z_value / 200.0) ** (1.0 / 1.6) if dbz > 0 else 0.0
                    predictions.append({
                        "time":        pred_time.isoformat().replace("+00:00", "Z"),
                        "time_offset": steps * 15,
                        "intensity":   dbz_to_intensity(dbz),
                        "dbz":         float(dbz),
                        "rain":        float(rain_mmhr),
                        "cluster":     cluster_label,
                        "src_x":       int(src_x),
                        "src_y":       int(src_y)
                    })
                    
                    if _DEV_CONFIG.get("verbose"):
                        logger.info(f"[VERBOSE] Step {steps} (+{offset_min}m): dbz={dbz:.1f} src=({src_x},{src_y}) cluster={cluster_label}")

                current_dbz = predictions[0]["dbz"]
                intensity   = predictions[0]["intensity"]
                summary_line = processor.render_rain_summary(
                    predictions=predictions,
                    time_offset_min=time_offset_min,
                    confidence_score=confidence_score,
                    approaching_clouds=clouds
                )
                # Sync cluster ETA with accurate pixel-level predictions
                if clouds:
                    for c in clouds:
                        c_lbl = c.get("label")
                        if not c_lbl: continue
                        for p in predictions:
                            if p["cluster"] == c_lbl and p["dbz"] >= 10.0:
                                c["eta_min"] = p["time_offset"]
                                break
                                
                    wind_speed = processor.get_wind_speed_kmh_from_vector(clouds[0]["vx"], clouds[0]["vy"])
                    wind_dir = processor.get_wind_direction_text_from_vector(clouds[0]["vx"], clouds[0]["vy"])
                    percent_change = clouds[0]["growth_rate"] * 100.0
                else:
                    wind_speed = processor.get_wind_speed_kmh(flow, px, py)
                    wind_dir = processor.get_wind_direction_text(flow, px, py)
                    percent_change = 0.0

                def render_hq_png(target_frame, pin_x, pin_y, time_utc, proc):
                    from PIL import Image, ImageFont, ImageDraw
                    import io
                    # Copy to avoid mutating original for future tasks
                    cf = target_frame.copy()
                    proc.draw_pin_on_frame(cf, pin_x, pin_y)
                    img_orig = Image.fromarray(cf)
                    img_hq = img_orig.resize((int(img_orig.width * 3.0), int(img_orig.height * 3.0)), Image.Resampling.NEAREST)

                    # Add IDC timestamp overlay
                    time_str = time_utc.astimezone(ZoneInfo('Asia/Bangkok')).strftime('%d %b %H:%M')
                    try:
                        fnt = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 120)
                    except Exception:
                        try:
                            fnt = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 140)
                        except Exception:
                            fnt = ImageFont.load_default()

                    draw = ImageDraw.Draw(img_hq, "RGBA")
                    if hasattr(draw, 'textbbox'):
                        left, top, right, bottom = draw.textbbox((0, 0), time_str, font=fnt)
                        text_w, text_h = right - left, bottom - top
                    else:
                        text_w, text_h = draw.textsize(time_str, font=fnt)

                    x_pos = img_hq.width - text_w - 80
                    y_pos = 80
                    pad = 40
                    draw.rectangle([x_pos - pad, y_pos - pad, x_pos + text_w + pad, y_pos + text_h + pad], fill=(0, 0, 0, 200))
                    draw.text((x_pos, y_pos), time_str, fill=(255, 255, 255, 255), font=fnt)

                    static_buffer = io.BytesIO()
                    img_hq.save(static_buffer, format='PNG')
                    return static_buffer.getvalue()

                static_bytes = None
                tracking_bytes = None
                timeline_bytes = None
                multiframe_bytes = None
                try:
                    static_bytes = await asyncio.to_thread(render_hq_png, curr_frame.copy(), user_px, user_py, now_utc, processor)
                    tracking_bytes = await asyncio.to_thread(
                        processor.generate_radar_tracking_image,
                        curr_frame.copy(), user_px, user_py, clouds, now_utc,
                        all_rain_clusters, predictions, True, True, time_offset_min
                    )
                    
                    # Create adjusted predictions for the timeline so it displays actual ETA from NOW
                    adjusted_predictions = []
                    for p in predictions:
                        adj_p = p.copy()
                        adj_p["time_offset"] = p["time_offset"] - time_offset_min
                        adjusted_predictions.append(adj_p)
                        
                    timeline_bytes = await asyncio.to_thread(processor.generate_timeline_image, adjusted_predictions)
                    
                    if len(frames) >= 2:
                        multiframe_bytes = await asyncio.to_thread(
                            processor.generate_multiframe_analysis_image,
                            frames, flow, user_px, user_py, clouds, processor, now_utc,
                            gap_min, frame_timestamps,
                        )
                except Exception as e:
                    logger.error(f"Failed to generate radar PNGs: {e}")
                
                return {
                    "predictions":       predictions,
                    "intensity":         intensity,
                    "max_rain":          max(p["rain"] for p in predictions) if predictions else 0.0,
                    "max_dbz":           float(max_dbz),
                    "duration_minutes":  sum(15 for p in predictions if p["dbz"] > 0),
                    "wind_speed_kmh":    round(wind_speed, 1),
                    "wind_dir_text":     wind_dir,
                    "endpoint":          f"tmd-radar ({station_code})",
                    "growth_rate_pct":   percent_change,
                    "approaching_clouds": clouds,
                    "rain_summary":      summary_line,
                    "is_outdated":       time_offset_min > 45,
                    "radar_gif_bytes":   None,
                    "radar_hq_gif_bytes": None,
                    "radar_static_bytes": static_bytes,
                    "radar_tracking_bytes": tracking_bytes,
                    "rain_timeline_bytes": timeline_bytes,
                    "radar_multiframe_bytes": multiframe_bytes,
                    "tmd_timestamp_utc": now_utc.isoformat(),
                    "tmd_timestamp_bkk": now_utc.astimezone(ZoneInfo('Asia/Bangkok')).strftime('%d %b %H:%M'),
                }
            except Exception as e:
                logger.warning(f"Failed to process TMD radar {station_code}: {e}")
                pass

        raise Exception("Location out of bounds for active TMD Radars.")
