import logging
import time
import os
import asyncio
import cv2
import io
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
from zoneinfo import ZoneInfo
from .tomorrow import TomorrowService
from .rainbow import RainbowService
from .xweather import XweatherService
from .open_meteo import OpenMeteoService
from .tmd_radar_processor import TMDRadarProcessor
logger = logging.getLogger(__name__)
from app.dependencies import get_repo_context

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
                    else:
                        async with get_repo_context() as repo:
                            cache = await repo.get_latest_radar_cache(station_code)
                        
                        frames = []
                        last_modified_dt = None
                        flow = None
                        frame_source = "static_cache"

                        if cache and cache.get("url_t") and cache.get("url_t_minus_1"):
                            # download images
                            bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "fonmayang.appspot.com")
                            from google.cloud import storage
                            client = storage.Client()
                            bucket = client.bucket(bucket_name)
                            blob_t = bucket.blob(cache["url_t"])
                            blob_t_minus_1 = bucket.blob(cache["url_t_minus_1"])
                            
                            try:
                                t_bytes, t_minus_1_bytes = await asyncio.gather(
                                    asyncio.to_thread(blob_t.download_as_bytes),
                                    asyncio.to_thread(blob_t_minus_1.download_as_bytes)
                                )
                            except Exception as e:
                                logger.warning(f"Failed to download cached frames for {station_code}: {e}")
                                t_bytes = None
                                t_minus_1_bytes = None

                            if t_bytes and t_minus_1_bytes:
                                t_np = np.frombuffer(t_bytes, np.uint8)
                                curr_frame = cv2.imdecode(t_np, cv2.IMREAD_COLOR)
                                curr_frame = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2RGB)
                                
                                t_minus_1_np = np.frombuffer(t_minus_1_bytes, np.uint8)
                                prev_frame = cv2.imdecode(t_minus_1_np, cv2.IMREAD_COLOR)
                                prev_frame = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2RGB)

                                if prev_frame.shape[:2] != curr_frame.shape[:2]:
                                    prev_frame = cv2.resize(
                                        prev_frame,
                                        (curr_frame.shape[1], curr_frame.shape[0]),
                                        interpolation=cv2.INTER_AREA,
                                    )
                                
                                frames = [prev_frame, curr_frame]
                                last_modified_dt = datetime.fromtimestamp(cache["timestamp"], timezone.utc)
                                flow = processor.calculate_optical_flow(frames)
                                _GLOBAL_TMD_CACHE[station_code] = (frames, last_modified_dt, time.time(), flow, frame_source)

                        if not frames or len(frames) < 2:
                            fresh_frames, fresh_dt, fresh_loop_bytes = await processor.fetch_loop_gif_and_extract_frames(use_cache=False)
                            if len(fresh_frames) >= 2:
                                frames = fresh_frames[-2:]
                                if frames[0].shape[:2] != frames[1].shape[:2]:
                                    frames[0] = cv2.resize(
                                        frames[0],
                                        (frames[1].shape[1], frames[1].shape[0]),
                                        interpolation=cv2.INTER_AREA,
                                    )
                                last_modified_dt = fresh_dt or datetime.now(timezone.utc)
                                flow = processor.calculate_optical_flow(frames)
                                frame_source = "loop_gif"
                                _GLOBAL_TMD_CACHE[station_code] = (frames, last_modified_dt, time.time(), flow, frame_source)
                                if fresh_loop_bytes:
                                    try:
                                        new_url_t = await processor.save_polled_frame(fresh_loop_bytes)
                                        async with get_repo_context() as repo:
                                            await repo.set_latest_radar_cache(
                                                station_code=station_code,
                                                url_t=new_url_t,
                                                url_t_minus_1=cache.get("url_t") if cache else None,
                                                timestamp=int((fresh_dt or datetime.now(timezone.utc)).timestamp()),
                                            )
                                    except Exception as e:
                                        logger.warning(f"Failed to warm radar cache for {station_code}: {e}")
                            else:
                                continue

                if not frames or len(frames) < 2:
                    continue

                curr_frame = frames[-1].copy()
                prev_frame = frames[-2].copy()
                use_loop_mapping = frame_source == "loop_gif"
                user_px, user_py = processor.latlng_to_pixel(lat, lng, is_loop=use_loop_mapping)
                import logging
                logging.info(f"DEBUG_LOCATION: lat={lat}, lng={lng} -> user_px={user_px}, user_py={user_py} (station: {station_code}, is_loop={use_loop_mapping})")
                if user_px is None or user_py is None:
                    continue

                # Find all cloud clusters approaching the user
                clouds = processor.find_approaching_clouds(
                    curr_frame, prev_frame, flow, user_px, user_py,
                    search_radius=80, min_dbz=20.0, cluster_dist=20,
                )

                # Apply mock overrides
                if mock_state in ("rain", "storm"):
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
                            bands = [
                                {"color": (46, 204, 113),  "dbz": 25.0, "base_offset": (-5, 5),   "eta": 0},  # Green
                                {"color": (241, 196, 15),  "dbz": 35.0, "base_offset": (-15, 15), "eta": 5},  # Yellow
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
                            vx, vy = 3.0, -3.0  # Move towards NE
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

                now_utc = last_modified_dt if last_modified_dt else datetime.now(timezone.utc)
                current_utc = datetime.now(timezone.utc)
                time_offset_min = (current_utc - now_utc).total_seconds() / 60.0

                summary_line = processor.render_rain_summary(clouds, confidence_cutoff_min=90, time_offset_min=time_offset_min)

                def dbz_to_intensity(d: float) -> str:
                    if d >= 55: return "ฝนตกหนักมาก"
                    if d >= 35: return "ฝนตกหนัก"
                    if d >= 20: return "ฝนตกปานกลาง"
                    if d > 0:   return "ฝนตกเล็กน้อย"
                    return "ไม่มีฝน"

                predictions = []
                max_dbz = 0.0
                current_dbz = processor.get_dbz_at_pixel(curr_frame, px, py)
                
                for steps in range(5):
                    offset_min = steps * 15
                    if steps == 0:
                        dbz = current_dbz
                    else:
                        dbz = 0.0
                        window_min = offset_min - 7.5
                        window_max = offset_min + 7.5
                        for c in clouds:
                            if window_min <= c["eta_min"] < window_max:
                                if c["predicted_dbz"] > dbz:
                                    dbz = c["predicted_dbz"]
                                    
                    if mock_state == "rain":
                        dbz = max(dbz, 40.0)
                    elif mock_state == "clear":
                        dbz = 0.0
                        
                    if dbz > max_dbz:
                        max_dbz = dbz
                    
                    pred_time  = now_utc + timedelta(minutes=steps * 15)
                    z_value    = 10 ** (dbz / 10.0)
                    rain_mmhr  = (z_value / 200.0) ** (1.0 / 1.6) if dbz > 0 else 0.0
                    predictions.append({
                        "time":        pred_time.isoformat().replace("+00:00", "Z"),
                        "time_offset": steps * 15,
                        "intensity":   dbz_to_intensity(dbz),
                        "dbz":         float(dbz),
                        "rain":        float(rain_mmhr),
                    })

                current_dbz = predictions[0]["dbz"]
                intensity   = predictions[0]["intensity"]
                
                if clouds:
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
                    
                    time_str = time_utc.astimezone(ZoneInfo('Asia/Bangkok')).strftime('%d %b %H:%M')
                    try:
                        fnt = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 96)
                    except:
                        try:
                            fnt = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 96)
                        except:
                            fnt = ImageFont.load_default()
                            
                    draw = ImageDraw.Draw(img_hq, "RGBA")
                    left, top, right, bottom = draw.textbbox((0, 0), time_str, font=fnt)
                    text_w, text_h = right - left, bottom - top
                    
                    x_pos = img_hq.width - text_w - 30
                    y_pos = 30
                    pad = 15
                    draw.rectangle([x_pos-pad, y_pos-pad, x_pos+text_w+pad, y_pos+text_h+pad], fill=(0, 0, 0, 200))
                    draw.text((x_pos, y_pos), time_str, fill=(255, 255, 255, 255), font=fnt)
                    
                    static_buffer = io.BytesIO()
                    img_hq.save(static_buffer, format='PNG')
                    return static_buffer.getvalue()

                static_bytes = None
                tracking_bytes = None
                timeline_bytes = None
                try:
                    static_bytes = await asyncio.to_thread(render_hq_png, curr_frame.copy(), user_px, user_py, now_utc, processor)
                    tracking_bytes = await asyncio.to_thread(processor.generate_radar_tracking_image, curr_frame.copy(), user_px, user_py, clouds)
                    timeline_bytes = await asyncio.to_thread(processor.generate_timeline_image, clouds)
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
                    "radar_gif_bytes":   None,
                    "radar_hq_gif_bytes": None,
                    "radar_static_bytes": static_bytes,
                    "radar_tracking_bytes": tracking_bytes,
                    "rain_timeline_bytes": timeline_bytes,
                }
            except Exception as e:
                logger.warning(f"Failed to process TMD radar {station_code}: {e}")
                pass

        raise Exception("Location out of bounds for active TMD Radars.")
