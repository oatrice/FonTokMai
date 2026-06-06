import logging
from typing import Optional
from .tomorrow import TomorrowService
from .rainbow import RainbowService
from .xweather import XweatherService
from .open_meteo import OpenMeteoService
from .tmd_radar_processor import TMDRadarProcessor

logger = logging.getLogger(__name__)

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
          Tomorrow.io → Rainbow Local → Rainbow Global

        พารามิเตอร์:
          force_endpoint: ถ้าระบุ ("global" หรือ "local") จะเรียก Rainbow endpoint นั้นโดยตรง
                          โดยไม่ผ่าน fallback chain (ใช้สำหรับ user สลับ endpoint เอง)
        """
        # --- โหมดบังคับ endpoint (ไม่ผ่าน fallback) ---
        if force_endpoint in ("global", "local"):
            try:
                result = await self.rainbow_svc.predict_rain_by_location(
                    lat, lng, endpoint_type=force_endpoint, mock_state=mock_state
                )
                endpoint_label = "rainbow-global" if force_endpoint == "global" else "rainbow-local"
                result["endpoint"] = endpoint_label
                logger.info(f"Successfully fetched weather from Rainbow ({force_endpoint}) [forced]")
                return result
            except Exception as e:
                logger.error(f"Rainbow ({force_endpoint}) failed (forced mode): {e}")
                return {
                    "predictions": [],
                    "intensity": "ไม่ทราบ",
                    "max_rain": 0.0,
                    "duration_minutes": 0,
                    "wind_speed_kmh": 0.0,
                    "endpoint": "error",
                }

        # --- โหมดปกติ: Auto-select based on accuracy score ---
        from app.dependencies import get_repo_context
        async with get_repo_context() as repo:
            reliabilities = await repo.get_all_api_reliability()
            
        sorted_endpoints = sorted(reliabilities.keys(), key=lambda k: reliabilities[k], reverse=True)
        
        service_map = {
            "xweather": lambda: self.xweather_svc.predict_rain_by_location(lat, lng, mock_state=mock_state),
            "tomorrow": lambda: self.tomorrow_svc.predict_rain_by_location(lat, lng, mock_state=mock_state),
            "rainbow-local": lambda: self.rainbow_svc.predict_rain_by_location(lat, lng, endpoint_type="local", mock_state=mock_state),
            "rainbow-global": lambda: self.rainbow_svc.predict_rain_by_location(lat, lng, endpoint_type="global", mock_state=mock_state),
            "open-meteo": lambda: self.open_meteo_svc.predict_rain_by_location(lat, lng, mock_state=mock_state),
            "tmd-radar": lambda: self._get_tmd_prediction(lat, lng, mock_state=mock_state)
        }
        
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
        import asyncio
        from app.dependencies import get_repo_context
        
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
                error_msg = str(e)
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

    async def _get_tmd_prediction(self, lat: float, lng: float, mock_state: Optional[str] = None) -> dict:
        """
        Wrapper for TMD Radar predictions using Optical Flow Nowcasting.
        Uses dot-product approach vector filter to find approaching cloud clusters,
        then ranks by ETA and generates a smart summary with growth/decay rates.
        """
        import cv2
        import numpy as np

        for station_code in ["kkn120", "kkn240", "skn240"]:
            try:
                processor = TMDRadarProcessor(station_code)
                px, py = processor.latlng_to_pixel(lat, lng)
                if px is None or py is None:
                    continue

                frames = await processor.fetch_loop_gif_and_extract_frames()
                if not frames or len(frames) < 2:
                    continue

                flow = processor.calculate_optical_flow(frames)
                curr_frame = frames[-1]
                prev_frame = frames[-2]

                # Find all cloud clusters approaching the user
                clouds = processor.find_approaching_clouds(
                    curr_frame, prev_frame, flow, px, py,
                    search_radius=80, min_dbz=20.0, cluster_dist=20,
                )

                # Apply mock overrides
                if mock_state == "rain":
                    if not clouds:
                        clouds = [{"eta_min": 10, "dbz_now": 40, "dbz_prev": 35,
                                   "growth_rate": 0.14, "predicted_dbz": 40,
                                   "dist": 10, "cx": px, "cy": py, "vx": 0, "vy": 0}]
                    else:
                        for c in clouds:
                            c["dbz_now"]       = max(c["dbz_now"], 40.0)
                            c["predicted_dbz"] = max(c["predicted_dbz"], 40.0)
                elif mock_state == "clear":
                    clouds = []

                # Generate smart summary text
                summary_line = processor.render_rain_summary(clouds, confidence_cutoff_min=90)

                # Build predictions array (keep legacy format for downstream consumers)
                def dbz_to_intensity(d: float) -> str:
                    if d >= 55: return "ฝนตกหนักมาก"
                    if d >= 35: return "ฝนตกหนัก"
                    if d >= 20: return "ฝนตกปานกลาง"
                    if d > 0:   return "ฝนตกเล็กน้อย"
                    return "ไม่มีฝน"

                from datetime import datetime, timedelta, timezone
                now_utc = datetime.now(timezone.utc)

                # Use closest approaching cloud for step-by-step predictions
                if clouds:
                    first_cloud = clouds[0]
                    rate = first_cloud["growth_rate"]
                    max_step = 0
                    max_raw_dbz = 0.0
                    for steps in range(5):
                        dbz = processor.extrapolate_rain_at_pixel(curr_frame, flow, px, py, steps, rate=0.0)
                        if dbz > max_raw_dbz:
                            max_raw_dbz = dbz
                            max_step = steps
                else:
                    rate = 0.0

                predictions = []
                max_dbz = 0.0
                for steps in range(5):
                    dbz = processor.extrapolate_rain_at_pixel(curr_frame, flow, px, py, steps, rate=rate)
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
                wind_speed  = processor.get_wind_speed_kmh(flow, px, py)
                percent_change = (clouds[0]["growth_rate"] * 100.0) if clouds else 0.0

                # Draw pins on all frames and generate GIF bytes
                gif_bytes    = None
                static_bytes = None
                try:
                    import io
                    from PIL import Image
                    pil_frames = []
                    for frame in frames:
                        processor.draw_pin_on_frame(frame, px, py)
                        pil_frames.append(Image.fromarray(frame))
                    if pil_frames:
                        buffer = io.BytesIO()
                        pil_frames[0].save(buffer, save_all=True, append_images=pil_frames[1:],
                                           format='GIF', loop=0, duration=500)
                        gif_bytes = buffer.getvalue()
                        static_buffer = io.BytesIO()
                        pil_frames[-1].save(static_buffer, format='PNG')
                        static_bytes = static_buffer.getvalue()
                        
                    # Also generate tracking and timeline images
                    tracking_bytes = processor.generate_radar_tracking_image(curr_frame, px, py, clouds)
                    timeline_bytes = processor.generate_timeline_image(clouds)
                except Exception as e:
                    logger.error(f"Failed to generate radar GIF/images: {e}")
                    tracking_bytes = None
                    timeline_bytes = None

                return {
                    "predictions":       predictions,
                    "intensity":         intensity,
                    "max_rain":          max(p["rain"] for p in predictions) if predictions else 0.0,
                    "max_dbz":           float(max_dbz),
                    "duration_minutes":  sum(15 for p in predictions if p["dbz"] > 0),
                    "wind_speed_kmh":    round(wind_speed, 1),
                    "endpoint":          f"tmd-radar ({station_code})",
                    "growth_rate_pct":   percent_change,
                    "approaching_clouds": clouds,
                    "rain_summary":      summary_line,
                    "radar_gif_bytes":   gif_bytes,
                    "radar_static_bytes": static_bytes,
                    "radar_tracking_bytes": tracking_bytes,
                    "rain_timeline_bytes": timeline_bytes,
                }
            except Exception as e:
                logger.warning(f"Failed to process TMD radar {station_code}: {e}")
                pass

        raise Exception("Location out of bounds for active TMD Radars.")

