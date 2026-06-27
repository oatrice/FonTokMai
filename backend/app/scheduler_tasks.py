import os
import time
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from app.dependencies import get_repo_context
from app.services.weather_manager import WeatherManager
from app.services.metrics_service import MetricsService
from app.services.telegram import send_telegram_message, send_telegram_document, send_telegram_photo, send_telegram_raw_document, get_radar_inline_keyboard, DEVELOPER_CHAT_IDS

logger = logging.getLogger(__name__)

# Minimum cooldown between alerts in minutes
ALERT_COOLDOWN_MINUTES = int(os.getenv("ALERT_COOLDOWN_MINUTES", "120"))
RAIN_TRIGGER_THRESHOLD_MM = float(os.getenv("RAIN_TRIGGER_THRESHOLD_MM", "0.5"))

# Use Thailand timezone for display
BKK_TZ = ZoneInfo("Asia/Bangkok")


import asyncio

async def _process_location(loc, repo, weather_manager, now, sem):
    async with sem:
        try:
            alerts_sent = 0
            errors = 0
            severity_escalated = False
            if loc.last_alerted_at:
                time_since_last_alert = now - loc.last_alerted_at
                if time_since_last_alert < timedelta(minutes=ALERT_COOLDOWN_MINUTES):
                    try:
                        mock_state_pre = await repo.get_mock_state(loc.chat_id)
                        pre_result = await weather_manager.predict_rain(loc.latitude, loc.longitude, mock_state=mock_state_pre)
                        current_max_rain = pre_result.get("max_rain", 0.0)
                        last_max_rain = loc.last_alert_max_rain or 0.0

                        if current_max_rain > last_max_rain and current_max_rain >= RAIN_TRIGGER_THRESHOLD_MM:
                            logger.info(
                                f"Smart Cooldown override for chat_id {loc.chat_id}: "
                                f"rain {last_max_rain:.1f} → {current_max_rain:.1f} mm/hr"
                            )
                            severity_escalated = True
                            result = pre_result
                        elif last_max_rain > 0.0 and current_max_rain < RAIN_TRIGGER_THRESHOLD_MM:
                            logger.info(f"Smart Cooldown override (All-Clear) for chat_id {loc.chat_id}")
                            result = pre_result
                        else:
                            logger.debug(
                                f"Skipping chat_id {loc.chat_id} (cooldown, "
                                f"rain {current_max_rain:.1f} mm/hr ≤ last {last_max_rain:.1f} mm/hr)"
                            )
                            return 0, 0
                    except Exception as e:
                        logger.warning(f"Smart Cooldown pre-check failed for {loc.chat_id}: {e}. Skipping.")
                        return 0, 0

            if not severity_escalated:
                mock_state = await repo.get_mock_state(loc.chat_id)
                result = await weather_manager.predict_rain(loc.latitude, loc.longitude, mock_state=mock_state)

            max_rain = result.get("max_rain", 0.0)
            if max_rain < RAIN_TRIGGER_THRESHOLD_MM:
                if loc.last_alert_max_rain and loc.last_alert_max_rain > 0.0:
                    logger.info(f"Sending All-Clear alert for chat_id {loc.chat_id}")
                    loc_name_str = f" '{loc.name.capitalize()}' " if loc.name and loc.name.lower() != "default" else " "
                    text = f"☀️ สภาพอากาศ ณ พิกัด{loc_name_str}เคลียร์แล้ว\n(ไม่มีแนวโน้มฝนตกในขณะนี้)"
                    await send_telegram_message(loc.chat_id, text)
                    await repo.update_last_alerted(loc, now, max_rain=0.0)
                else:
                    logger.debug(f"Skipping alert for {loc.chat_id}: Max rain {max_rain} mm/hr < threshold {RAIN_TRIGGER_THRESHOLD_MM}")
                return 0, 0

            predictions = result.get("predictions", [])
            eta_minutes = None
            rain_start_dt = None

            if predictions:
                try:
                    base_time = datetime.fromisoformat(predictions[0].get("time", "").replace("Z", "+00:00"))
                except Exception:
                    base_time = None
                    
                for pred in predictions:
                    if pred.get("rain", 0) >= RAIN_TRIGGER_THRESHOLD_MM:
                        if base_time:
                            try:
                                pred_time = datetime.fromisoformat(pred.get("time", "").replace("Z", "+00:00"))
                                current_utc = datetime.now(timezone.utc)
                                eta_minutes = int((pred_time - current_utc).total_seconds() / 60)
                                if eta_minutes < 0:
                                    eta_minutes = 0
                                rain_start_dt = pred_time
                            except Exception:
                                eta_minutes = 0
                        else:
                            eta_minutes = 0
                        break

            if eta_minutes is not None and eta_minutes <= 60:
                intensity_str = result.get("intensity", "ไม่ทราบ")
                duration_min = result.get("duration_minutes", 0)
                wind_speed_kmh = result.get("wind_speed_kmh", 0.0)
                endpoint_source = result.get("endpoint", "unknown")
                
                source_name = endpoint_source
                if endpoint_source == "tomorrow": source_name = "Tomorrow.io"
                elif endpoint_source == "rainbow-local": source_name = "Rainbow (Local)"
                elif endpoint_source == "rainbow-global": source_name = "Rainbow (Global)"
                
                loc_name_str = f" '{loc.name.capitalize()}' " if loc.name and loc.name.lower() != "default" else " "
                
                if not rain_start_dt:
                    rain_start_dt = datetime.now(timezone.utc) + timedelta(minutes=eta_minutes)
                    
                rain_end_dt = rain_start_dt + timedelta(minutes=duration_min)
                start_time_str = rain_start_dt.astimezone(BKK_TZ).strftime("%H:%M น.")
                end_time_str = rain_end_dt.astimezone(BKK_TZ).strftime("%H:%M น.")
                distance_km = (eta_minutes / 60.0) * wind_speed_kmh
                
                text = ""
                if severity_escalated:
                    last_rain_val = loc.last_alert_max_rain or 0.0
                    text += f"⚠️ *อัปเดต: ฝนทวีความรุนแรงขึ้น!*\n({last_rain_val:.1f} mm/hr → {max_rain:.1f} mm/hr)\n\n"

                if eta_minutes == 0: text += f"🌧️ ฝนกำลังตกอยู่ที่พิกัด{loc_name_str}ของคุณ ณ ขณะนี้\n"
                else:
                    text += f"🌧️ ฝนกำลังเคลื่อนมาทางพิกัด{loc_name_str}ของคุณ\n"
                    text += f"⏰ จะเริ่มตกเวลา: {start_time_str} (ในอีก {eta_minutes} นาที)\n"
                
                duration_text = f"ตกต่อเนื่อง {duration_min} นาที"
                if duration_min >= 60:
                    hrs = duration_min // 60
                    mins = duration_min % 60
                    duration_text = f"ตกต่อเนื่อง {hrs} ชม. {mins} นาที" if mins > 0 else f"ตกต่อเนื่อง {hrs} ชม."
                    
                if duration_min > 0: text += f"🛑 คาดว่าจะหยุดเวลา: {end_time_str} ({duration_text})\n\n"
                else: text += "\n"
                    
                if intensity_str == "ไม่มีฝน" and eta_minutes > 0:
                    if max_rain > 10.0: max_int = "ฝนตกหนักมาก"
                    elif max_rain > 2.5: max_int = "ฝนตกหนัก"
                    elif max_rain > 0.5: max_int = "ฝนตกปานกลาง"
                    else: max_int = "ฝนตกเล็กน้อย"
                    text += f"💧 ความรุนแรง (สูงสุด): {max_int} ({max_rain:.1f} mm/hr)\n"
                else:
                    text += f"💧 ความรุนแรง: {intensity_str} ({max_rain:.1f} mm/hr)\n"
                
                wind_dir_text = result.get("wind_dir_text", "ไม่ทราบ")
                if wind_speed_kmh > 0: text += f"🌬️ สภาพลม: {wind_speed_kmh:.1f} km/h (พัดไปทางทิศ {wind_dir_text})\n"
                if eta_minutes > 0 and wind_speed_kmh > 0: text += f"📏 ระยะห่างจากกลุ่มฝน: ประมาณ {distance_km:.1f} กม.\n"
                    
                rain_summary = result.get("rain_summary")
                if rain_summary:
                    text += f"{rain_summary}\n"

                # Growth/decay trend — แสดงเสมอ ไม่ว่าจะมี rain_summary หรือไม่
                growth_rate = result.get("growth_rate_pct")
                if growth_rate is not None and "ไม่พบฝน" not in (rain_summary or ""):
                    if growth_rate > 5.0:
                        text += f"📈 แนวโน้มกลุ่มฝน: กำลังก่อตัวแรงขึ้น (+{growth_rate:.1f}%/15min)\n"
                    elif growth_rate < -5.0:
                        text += f"📉 แนวโน้มกลุ่มฝน: อ่อนกำลังลง ({growth_rate:.1f}%/15min)\n"
                    else:
                        text += f"➖ แนวโน้มกลุ่มฝน: คงที่\n"
                        
                text += f"📡 แหล่งข้อมูล: {source_name}\n"
                bkk_tz = timezone(timedelta(hours=7))
                update_time_str = datetime.now(bkk_tz).strftime("%d/%m/%Y %H:%M:%S")
                text += f"🔄 ข้อมูลอัปเดตล่าสุด: {update_time_str}\n"
                    
                is_dev = str(loc.chat_id) in DEVELOPER_CHAT_IDS
                reply_markup = get_radar_inline_keyboard(loc.latitude, loc.longitude, is_developer=is_dev)
                
                r_lat = round(loc.latitude, 4)
                r_lng = round(loc.longitude, 4)
                reply_markup["inline_keyboard"].append([{"text": "📊 เทียบข้อมูล", "callback_data": f"compare_api_{r_lat}_{r_lng}"}])
                ep_map = {"tomorrow": "t", "rainbow-local": "rl", "rainbow-global": "rg", "xweather": "xw", "open-meteo": "om"}
                ep_code = ep_map.get(result.get("endpoint"), "u")
                cb_data = f"fb_falsealarm_{r_lat}_{r_lng}_{ep_code}_{max_rain:.1f}"
                reply_markup["inline_keyboard"].append([{"text": "❌ แจ้งเตือนผิดพลาด (ฝนไม่ตกจริง)", "callback_data": cb_data}])
                
                logger.info(f"Alerting chat_id {loc.chat_id}: ETA {eta_minutes} mins")
                await send_telegram_message(loc.chat_id, text, reply_markup=reply_markup)
                
                gif_bytes = result.get("radar_gif_bytes")
                static_bytes = result.get("radar_static_bytes")
                tracking_bytes = result.get("radar_tracking_bytes")
                timeline_bytes = result.get("rain_timeline_bytes")
                
                if static_bytes: await send_telegram_photo(loc.chat_id, static_bytes, "radar_latest.png")
                if timeline_bytes: await send_telegram_photo(loc.chat_id, timeline_bytes, "rain_timeline.png")
                if tracking_bytes: await send_telegram_photo(loc.chat_id, tracking_bytes, "radar_tracking.png")
                if gif_bytes: await send_telegram_document(loc.chat_id, gif_bytes, "radar_nowcast.gif")
                
                await repo.update_last_alerted(loc, now, max_rain=max_rain)
                
                try:
                    advanced_data = await weather_manager.get_advanced_alerts(loc.latitude, loc.longitude, mock_state=mock_state)
                    has_advisory = len(advanced_data.get("advisories", [])) > 0
                    has_lightning = advanced_data.get("lightning") is not None
                    has_stormcell = advanced_data.get("stormcell") is not None
                    
                    if has_advisory or has_lightning or has_stormcell:
                        adv_text = "🚨 *ข้อมูลเตือนภัยขั้นสูงรอบตัวคุณ*\n\n"
                        if has_advisory:
                            for adv in advanced_data["advisories"]: adv_text += f"⚠️ ประกาศเตือนภัย: {adv.get('name', '')}\n"
                            adv_text += "\n"
                        if has_lightning:
                            lightning = advanced_data["lightning"]
                            adv_text += f"⚡ ฟ้าผ่าระยะใกล้สุด: {lightning.get('distance_km', 0):.1f} กม.\n\n"
                        if has_stormcell:
                            stormcell = advanced_data["stormcell"]
                            if stormcell.get('distance_km') is None:
                                adv_text += f"🌪️ แนวโน้มกลุ่มฝน/ลม (Contingency):\n"
                                adv_text += f"   - ทิศทาง: {stormcell.get('direction', 'N/A')}\n"
                                adv_text += f"   - ความเร็วลม: {stormcell.get('speed_kmh', 0):.1f} km/h\n\n"
                                adv_text += "ℹ️ ข้อมูลขั้นสูงจาก Open-Meteo (Fallback)"
                            else:
                                adv_text += f"🌪️ ตรวจพบกลุ่มพายุ: ระยะห่าง {stormcell.get('distance_km', 0):.1f} กม.\n"
                                adv_text += f"   - ทิศทาง: {stormcell.get('direction', 'N/A')}\n"
                                adv_text += f"   - ความเร็ว: {stormcell.get('speed_kmh', 0):.1f} km/h\n"
                                adv_text += f"   - ความรุนแรงสูงสุด (dBZ): {stormcell.get('max_dbz', 0)}\n\n"
                                adv_text += "ℹ️ ข้อมูลขั้นสูงจาก Xweather"
                        elif has_advisory or has_lightning:
                            adv_text += "ℹ️ ข้อมูลขั้นสูงจาก Xweather"
                        await send_telegram_message(loc.chat_id, adv_text)
                except Exception as e:
                    logger.error(f"Failed to process advanced alerts for {loc.chat_id}: {e}")
                    errors += 1
                
                alerts_sent += 1
                return alerts_sent, errors

            return 0, 0
        except Exception as e:
            logger.error(f"Failed to check rain for chat_id {loc.chat_id}: {e}")
            return 0, 1


async def run_alert_for_locations(target_locs: list):
    """Run the rain check and alert pipeline for a specific list of locations only.
    Used by /devmock scenario loc:name to fire an alert for a single saved location
    without triggering the full scheduler sweep.
    """
    try:
        await fetch_tmd_radar_routine()
    except Exception as e:
        logger.error(f"[run_alert_for_locations] Radar fetch error: {e}")

    async with get_repo_context() as repo:
        weather_manager = WeatherManager()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        sem = asyncio.Semaphore(5)
        tasks = [_process_location(loc, repo, weather_manager, now, sem) for loc in target_locs]
        await asyncio.gather(*tasks, return_exceptions=True)


async def check_rain_and_alert():
    logger.info("Starting proactive rain check...")
    start_time = time.time()
    alerts_sent = 0
    errors = 0
    
    try:
        await fetch_tmd_radar_routine()
    except Exception as e:
        logger.error(f"Error during cache phase: {e}")
    
    async with get_repo_context() as repo:
        locations = await repo.get_active_locations()
        if not locations:
            logger.info("No active locations to check.")
            return

        weather_manager = WeatherManager()
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        sem = asyncio.Semaphore(15)
        tasks = [_process_location(loc, repo, weather_manager, now, sem) for loc in locations]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for r in results:
            if isinstance(r, tuple):
                alerts_sent += r[0]
                errors += r[1]
            elif isinstance(r, Exception):
                logger.error(f"Task raised an unhandled exception: {r}")
                errors += 1
                
        duration_s = time.time() - start_time
        try:
            metrics_svc = MetricsService(repo)
            await metrics_svc.record_cron_run(
                routine_name="check_rain",
                duration_s=duration_s,
                alerts_sent=alerts_sent,
                locations_checked=len(locations),
                errors=errors
            )
        except Exception as e:
            logger.error(f"Failed to save metrics for check_rain: {e}")


async def check_disasters_frequent_routine():
    """Run frequently (e.g., every 1 min) for USGS Earthquakes."""
    logger.info("Starting frequent disaster check (USGS Earthquakes)...")
    from app.services.earthquake import fetch_usgs_geojson
    from app.services.disaster_manager import process_disaster_event
    
    events = await fetch_usgs_geojson()
    if not events:
        return
        
    async with get_repo_context() as repo:
        for event in events:
            await process_disaster_event(repo, "earthquake", event)

async def check_disasters_infrequent_routine():
    """Run infrequently (e.g., every 30-60 mins) for Xweather Cyclones/Fires."""
    logger.info("Starting infrequent disaster check (Xweather Cyclones & Fires)...")
    from app.services.xweather import XweatherService
    from app.services.disaster_manager import process_disaster_event
    
    xweather = XweatherService()
    
    cyclones = await xweather.get_active_tropical_cyclones()
    fires = await xweather.get_active_fires()
    
    async with get_repo_context() as repo:
        for event in cyclones:
            await process_disaster_event(repo, "cyclone", event)
        for event in fires:
            await process_disaster_event(repo, "fire", event)

async def fetch_tmd_radar_routine():
    """Run frequently (e.g., every 5 mins) to fetch and cache TMD Radar images to Firebase Storage and Firestore.
    
    Processes all stations in PARALLEL using asyncio.gather for improved performance.
    """
    logger.info("Starting TMD Radar Cache Phase...")
    import time
    start_time = time.time()
    errors = 0
    stations_updated = 0

    from app.services.tmd_radar_processor import TMDRadarProcessor
    from app.dependencies import get_repo_context
    from app.services.metrics_service import MetricsService
    import httpx
    import asyncio

    stations_to_update = ["kkn120", "kkn240", "skn240"]

    async def _process_station(station: str) -> dict:
        result = {"station": station, "updated": False, "error": None}
        try:
            processor = TMDRadarProcessor(station_code=station)

            # 1. Fetch static image bytes
            static_bytes = await processor.fetch_latest_image_bytes()
            if not static_bytes:
                logger.warning(f"[{station}] Could not fetch static image.")
                # We do not return early here because we might still want to trigger GIF fallback!

            # 2. Extract timestamp via OCR
            from app.services.ocr_service import OCRService
            import numpy as np
            import cv2
            
            ocr_svc = OCRService()
            now_ts = int(datetime.now(timezone.utc).timestamp())
            
            ts = None
            frame = None
            np_arr = None
            
            if static_bytes:
                np_arr = np.frombuffer(static_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                # Since OpenCV reads in BGR, we convert to RGB for consistency with original PIL logic
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                logger.info(f"[{station}] ✅ Static fetch OK — {len(static_bytes):,} bytes, shape={frame.shape[:2]}")
                ts = await ocr_svc.get_frame_timestamp(frame, fallback_ts=now_ts)
                ocr_ok = ts is not None and ts != now_ts
                if ocr_ok:
                    from zoneinfo import ZoneInfo
                    _bkk = ZoneInfo("Asia/Bangkok")
                    _dt  = datetime.fromtimestamp(ts, _bkk).strftime("%H:%M:%S")
                    logger.info(f"[{station}] 🔍 OCR resolved ts={ts} ({_dt} BKK) — from cache or live OCR")
                else:
                    logger.warning(
                        f"[{station}] ⚠️  OCR failed (fallback_ts={ts} = wall-clock) — "
                        f"frame will NOT be saved to avoid corrupting sliding window"
                    )
                    ts = None  # Treat as if static had no valid timestamp
            else:
                logger.warning(f"[{station}] ❌ Static fetch FAILED — will attempt GIF fallback if enabled")

            # 3. Check cache
            async with get_repo_context() as repo:
                cache = await repo.get_latest_radar_cache(station)
                
                frames = cache.get("frames", []) if cache else []
                latest_ts = frames[0]["timestamp"] if frames else 0
                last_gif_fallback_time = cache.get("last_gif_fallback_time", 0.0) if cache else 0.0

                # Sanity-check: if latest_ts is in the future (e.g. corrupted wall-clock fallback),
                # reset to 0 so a fresh valid OCR timestamp can replace it.
                if latest_ts > now_ts + 300:  # >5 min in the future = clearly corrupt
                    logger.warning(
                        f"[{station}] ⚠️  Firestore latest_ts={latest_ts} is in the future "
                        f"(now={now_ts}, delta={latest_ts - now_ts}s) — resetting to 0 to unblock cache"
                    )
                    latest_ts = 0

                
                needs_fallback = False
                fallback_reason = ""
                
                # Check for dead static image BEFORE the early return
                sys_settings = await repo.get_system_settings()
                enable_fallback_db = sys_settings.get("enable_gif_fallback", True)
                enable_fallback_env = os.environ.get("ENABLE_TMD_GIF_FALLBACK", "true").lower() == "true"
                enable_fallback = enable_fallback_db and enable_fallback_env
                
                if enable_fallback:
                    if frames:
                        gap_to_now = (now_ts - latest_ts) / 60.0
                        if gap_to_now > 60.0 and (now_ts - last_gif_fallback_time) > 1800.0:
                            needs_fallback = True
                            fallback_reason = f"Static dead for {gap_to_now:.1f}m"
                    else:
                        if (now_ts - last_gif_fallback_time) > 1800.0:
                            needs_fallback = True
                            fallback_reason = "Cache is empty"

                # Bootstrap: Firestore has <2 frames regardless of static freshness.
                # Must be checked BEFORE the early return so stations with unchanged
                # images (ts == latest_ts) still get GIF bootstrapped.
                if enable_fallback and not needs_fallback and len(frames) < 2:
                    if (now_ts - last_gif_fallback_time) > 1800.0:
                        needs_fallback = True
                        fallback_reason = f"Cache has <2 frames ({len(frames)})"

                # If we already have this timestamp (or static is down) and no fallback is needed, do nothing
                if not needs_fallback and ((ts and ts <= latest_ts) or not static_bytes):
                    logger.debug(f"[{station}] Image unchanged or unavailable (ts {ts}). Skipping.")
                    return result

                # It's a new image! Only insert if OCR succeeded (ts is not None) and it's newer.
                # If OCR failed, ts=None → skip saving to avoid wall-clock timestamps in the window.
                new_url = None
                if ts and ts > latest_ts:
                    logger.info(f"[{station}] 🆕 New frame detected (ts={ts} > latest={latest_ts}) — saving to Firestore")
                    new_url = await processor.save_polled_frame(static_bytes)
                    frames.insert(0, {"url": new_url, "timestamp": ts})
                    # Ensure monotonic order after insert
                    frames = sorted(frames, key=lambda f: f["timestamp"])
                    frames.reverse()  # newest first
                elif ts:
                    logger.info(f"[{station}] ♻️  Frame unchanged (ts={ts} == latest={latest_ts}) — no write needed")


                    
                if needs_fallback:
                    logger.warning(f"[{station}] GIF fallback triggered: {fallback_reason}")
                    last_gif_fallback_time = now_ts # Update the attempt time

                if needs_fallback:
                    logger.info(f"[{station}] Executing GIF fallback recovery...")
                    fallback_frames_data, fallback_dt, loop_bytes = await processor.fetch_loop_gif_and_extract_frames()
                    if fallback_frames_data and len(fallback_frames_data) >= 2:
                        logger.info(f"[{station}] 🌀 GIF fallback: fetched {len(fallback_frames_data)} frames from loop GIF")
                        # Keep up to 6 newest frames and reverse so newest is first
                        recent_fallback = fallback_frames_data[-6:]
                        recent_fallback.reverse()

                        new_frames_list = []
                        base_ts = ts if ts else now_ts
                        for i, f_img in enumerate(recent_fallback):
                            f_ts = await ocr_svc.get_frame_timestamp(f_img, fallback_ts=base_ts - i * 900)
                            # Resize to 800×800 so weather_manager's is_loop detection
                            # (frame.shape < 800) does NOT misfire on these frames,
                            # ensuring static pixel coordinates are used for optical flow.
                            if f_img.shape[0] != 800 or f_img.shape[1] != 800:
                                f_img = cv2.resize(f_img, (800, 800), interpolation=cv2.INTER_NEAREST)
                            is_success, buffer = cv2.imencode(".png", cv2.cvtColor(f_img, cv2.COLOR_RGB2BGR))
                            if is_success:
                                f_url = await processor.save_polled_frame(buffer.tobytes())
                                new_frames_list.append({"url": f_url, "timestamp": f_ts})


                        if new_frames_list:
                            gif_newest_ts    = new_frames_list[0]["timestamp"]
                            current_newest_ts = frames[0]["timestamp"] if frames else 0

                            # Bootstrap case: Firestore had <2 frames before fallback.
                            # Use GIF frames as historical context (older frames), then
                            # place the fresh static frame on top if it's newer.
                            # Do NOT discard GIF even though gif_newest_ts < static_ts.
                            is_bootstrap = fallback_reason.startswith("Cache has <2") or fallback_reason == "Cache is empty"

                            if is_bootstrap:
                                # Merge: static (newest) + GIF history (older context)
                                if ts and ts > gif_newest_ts:
                                    new_frames_list.insert(0, {"url": new_url, "timestamp": ts})
                                frames = new_frames_list
                                logger.info(
                                    f"[{station}] 🌀 Bootstrap: merged static+GIF → "
                                    f"{len(frames)} frames (static={ts}, gif_newest={gif_newest_ts})"
                                )
                            elif gif_newest_ts > current_newest_ts + 300:
                                # Dead static image: only adopt GIF if it has genuinely newer data
                                logger.info(f"[{station}] GIF data is newer (GIF: {gif_newest_ts}, Static: {current_newest_ts}). Adopting GIF frames.")
                                if ts and ts > gif_newest_ts:
                                    new_frames_list.insert(0, {"url": new_url, "timestamp": ts})
                                frames = new_frames_list
                            else:
                                logger.warning(f"[{station}] GIF data is NOT newer (GIF: {gif_newest_ts}, Static: {current_newest_ts}). Discarding GIF.")

                    else:
                        logger.warning(f"[{station}] 🌀 GIF fallback: failed to extract ≥2 frames from loop GIF")
                
                frames = frames[:6] # Keep max 6 frames
                
                await repo.set_latest_radar_cache(
                    station_code=station,
                    frames=frames,
                    last_gif_fallback_time=last_gif_fallback_time
                )
                logger.info(f"Updated Firestore radar cache for {station} with {len(frames)} frames, latest ts {ts}")

            # Cleanup old frames
            deleted = await processor.cleanup_old_frames(max_age_hours=3)
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old frames for {station}")

            # Clean up memory explicitly
            if frame is not None:
                del frame
            if np_arr is not None:
                del np_arr
            import gc
            gc.collect()

            result["updated"] = True
        except Exception as e:
            logger.error(f"Failed to cache TMD radar for {station}: {e}")
            result["error"] = str(e)
        return result

    # Run all stations in PARALLEL — reduces total time from 3×T to max(T)
    station_results = await asyncio.gather(
        *[_process_station(s) for s in stations_to_update],
        return_exceptions=True
    )

    for res in station_results:
        if isinstance(res, Exception):
            logger.error(f"Unhandled exception in station task: {res}")
            errors += 1
        elif isinstance(res, dict):
            if res.get("updated"):
                stations_updated += 1
            if res.get("error"):
                errors += 1

    # Record Metrics
    duration_s = time.time() - start_time
    logger.info(f"TMD Radar Cache Phase complete: {stations_updated}/{len(stations_to_update)} stations, {duration_s:.1f}s")
    try:
        async with get_repo_context() as repo:
            metrics_svc = MetricsService(repo)
            await metrics_svc.record_cron_run(
                routine_name="fetch_tmd_radar",
                duration_s=duration_s,
                errors=errors,
                extra_data={"stations_updated": stations_updated}
            )
    except Exception as e:
        logger.error(f"Failed to save metrics for fetch_tmd_radar: {e}")




async def trigger_mock_disaster(payload_dict: dict):
    """Process a mock disaster payload."""
    import time
    from app.dependencies import get_repo_context
    from app.services.disaster_manager import process_disaster_event
    
    timestamp = int(time.time())
    event_id = f"postman_mock_{timestamp}"
    
    event_data = {
        "id": event_id,
        "lat": payload_dict.get("lat"),
        "lng": payload_dict.get("lng"),
    }
    
    disaster_type = payload_dict.get("type", "earthquake")
    
    if disaster_type == "earthquake":
        event_data["mag"] = payload_dict.get("mag")
        event_data["place"] = payload_dict.get("name")
    elif disaster_type == "cyclone":
        event_data["name"] = payload_dict.get("name")
        event_data["category"] = "Cat 4"
    elif disaster_type == "fire":
        event_data["name"] = payload_dict.get("name")
        
    async with get_repo_context() as repo:
        await process_disaster_event(repo, disaster_type, event_data)
