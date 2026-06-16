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
        self.tmd_frames_cache = {}

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
            "tmd-radar": lambda: self._get_tmd_prediction(lat, lng, mock_state=mock_state)
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
        from app.dependencies import get_repo_context
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

                if station_code in self.tmd_frames_cache:
                    frames, last_modified_dt = self.tmd_frames_cache[station_code]
                else:
                    frames, last_modified_dt = await processor.fetch_loop_gif_and_extract_frames()
                    if frames and len(frames) >= 2:
                        self.tmd_frames_cache[station_code] = (frames, last_modified_dt)

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
                if mock_state in ("rain", "storm"):
                    import cv2
                    
                    if mock_state == "storm" or not clouds:
                        if mock_state == "storm":
                            clouds = []  # Forcefully clear real clouds to ensure mock storm always shows
                        mock_configs = []
                        if mock_state == "storm":
                            # 5-color huge broad front (randomized for testing)
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
                            # Just a simple rain cell for normal testing when sky is clear
                            bands = [
                                {"color": (46, 204, 113),  "dbz": 25.0, "base_offset": (-5, 5),   "eta": 0},  # Green
                                {"color": (241, 196, 15),  "dbz": 35.0, "base_offset": (-15, 15), "eta": 5},  # Yellow
                            ]
                            
                        for band in bands:
                            bx, by = band["base_offset"]
                            # Spread clouds along the NW-SE axis (dx=spread, dy=spread)
                            for spread in [-60, -30, 0, 30, 60]:
                                mock_configs.append({
                                    "color": band["color"],
                                    "dbz": band["dbz"],
                                    "offset": (bx + spread, by + spread),
                                    "eta": band["eta"]
                                })

                        for mc in mock_configs:
                            cx, cy = px + mc["offset"][0], py + mc["offset"][1]
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
                            # Draw fake cloud blobs moving across the frames
                            num_frames = len(frames)
                            for i, f in enumerate(frames):
                                steps_ago = num_frames - 1 - i
                                cx_i = int(cx - steps_ago * vx)
                                cy_i = int(cy - steps_ago * vy)
                                if mock_state == "storm":
                                    # Make the blobs slightly larger so they merge into a solid wall
                                    cv2.circle(f, (cx_i, cy_i), 22, mc["color"], -1)
                    else:
                        # If there ARE real clouds and mock_state == "rain", we just boost their intensity
                        # to simulate heavier rain without injecting fake clouds.
                        for c in clouds:
                            c["dbz_now"]       = max(c["dbz_now"], 40.0)
                            c["predicted_dbz"] = max(c["predicted_dbz"], 40.0)
                elif mock_state == "clear":
                    clouds = []

                from datetime import datetime, timedelta, timezone
                if last_modified_dt:
                    now_utc = last_modified_dt
                else:
                    now_utc = datetime.now(timezone.utc)
                
                current_utc = datetime.now(timezone.utc)
                time_offset_min = (current_utc - now_utc).total_seconds() / 60.0

                # Generate smart summary text
                summary_line = processor.render_rain_summary(clouds, confidence_cutoff_min=90, time_offset_min=time_offset_min)

                # Build predictions array (keep legacy format for downstream consumers)
                def dbz_to_intensity(d: float) -> str:
                    if d >= 55: return "ฝนตกหนักมาก"
                    if d >= 35: return "ฝนตกหนัก"
                    if d >= 20: return "ฝนตกปานกลาง"
                    if d > 0:   return "ฝนตกเล็กน้อย"
                    return "ไม่มีฝน"

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

                # Draw pins on all frames and generate GIF bytes
                gif_bytes    = None
                hq_gif_bytes = None
                static_bytes = None
                try:
                    import io
                    from PIL import Image, ImageDraw, ImageFont
                    from zoneinfo import ZoneInfo
                    
                    try:
                        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
                    except:
                        try:
                            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 48)
                        except:
                            font = ImageFont.load_default()
                        
                    pil_frames_std = []
                    pil_frames_hq = []
                    num_frames = len(frames)
                    for i, frame in enumerate(frames):
                        processor.draw_pin_on_frame(frame, px, py)
                        img_orig = Image.fromarray(frame)
                        
                        # Upscale 1.5x for standard animation
                        img_std = img_orig.resize((int(img_orig.width * 1.5), int(img_orig.height * 1.5)), Image.Resampling.NEAREST)
                        # Upscale 3.0x for HQ document
                        img_hq = img_orig.resize((int(img_orig.width * 3.0), int(img_orig.height * 3.0)), Image.Resampling.NEAREST)
                        
                        # Calculate time for this frame
                        frames_ago = num_frames - 1 - i
                        frame_time_utc = now_utc - timedelta(minutes=15 * frames_ago)
                        frame_time_bkk = frame_time_utc.astimezone(ZoneInfo('Asia/Bangkok'))
                        time_str = frame_time_bkk.strftime('%d %b %H:%M')
                        
                        # Helper to draw timestamp
                        def draw_timestamp(img, scale_factor):
                            # Scale font size roughly
                            fnt = font
                            try:
                                fnt = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(32 * scale_factor))
                            except:
                                try:
                                    fnt = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", int(32 * scale_factor))
                                except:
                                    fnt = ImageFont.load_default()
                                
                            draw = ImageDraw.Draw(img, "RGBA")
                            left, top, right, bottom = draw.textbbox((0, 0), time_str, font=fnt)
                            text_w = right - left
                            text_h = bottom - top
                            
                            x_pos = img.width - text_w - int(10 * scale_factor)
                            y_pos = int(10 * scale_factor)
                            
                            pad = int(5 * scale_factor)
                            draw.rectangle([x_pos-pad, y_pos-pad, x_pos+text_w+pad, y_pos+text_h+pad], fill=(0, 0, 0, 200))
                            draw.text((x_pos, y_pos), time_str, fill=(255, 255, 255, 255), font=fnt)
                            return img
                            
                        pil_frames_std.append(draw_timestamp(img_std, 1.5))
                        pil_frames_hq.append(draw_timestamp(img_hq, 3.0))
                    if pil_frames_std and pil_frames_hq:
                        buffer = io.BytesIO()
                        hq_buffer = io.BytesIO()
                        
                        durations = [500] * len(pil_frames_std)
                        durations[-1] = 3000  # Freeze last frame for 3 seconds
                        
                        pil_frames_std[0].save(buffer, save_all=True, append_images=pil_frames_std[1:],
                                               format='GIF', loop=0, duration=durations, optimize=True)
                        gif_bytes = buffer.getvalue()
                        
                        pil_frames_hq[0].save(hq_buffer, save_all=True, append_images=pil_frames_hq[1:],
                                              format='GIF', loop=0, duration=durations, optimize=True)
                        hq_gif_bytes = hq_buffer.getvalue()
                        
                        static_buffer = io.BytesIO()
                        pil_frames_hq[-1].save(static_buffer, format='PNG')
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
                    "wind_dir_text":     wind_dir,
                    "endpoint":          f"tmd-radar ({station_code})",
                    "growth_rate_pct":   percent_change,
                    "approaching_clouds": clouds,
                    "rain_summary":      summary_line,
                    "radar_gif_bytes":   gif_bytes,
                    "radar_hq_gif_bytes": hq_gif_bytes,
                    "radar_static_bytes": static_bytes,
                    "radar_tracking_bytes": tracking_bytes,
                    "rain_timeline_bytes": timeline_bytes,
                }
            except Exception as e:
                logger.warning(f"Failed to process TMD radar {station_code}: {e}")
                pass

        raise Exception("Location out of bounds for active TMD Radars.")

