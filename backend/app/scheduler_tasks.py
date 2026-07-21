import os
import time
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from app.dependencies import get_repo_context
from app.services.weather_manager import WeatherManager
from app.services.metrics_service import MetricsService
from app.services.telegram import send_telegram_message, send_telegram_document, send_telegram_photo, send_telegram_raw_document, get_radar_inline_keyboard, DEVELOPER_CHAT_IDS
from app.services.notification import get_notification_service

logger = logging.getLogger(__name__)

# Minimum cooldown between alerts in minutes
ALERT_COOLDOWN_MINUTES = int(os.getenv("ALERT_COOLDOWN_MINUTES", "120"))
RAIN_TRIGGER_THRESHOLD_MM = float(os.getenv("RAIN_TRIGGER_THRESHOLD_MM", "0.5"))

# Use Thailand timezone for display
BKK_TZ = ZoneInfo("Asia/Bangkok")


import asyncio

async def _evaluate_location(loc, repo, weather_manager, now, sem):
    async with sem:
        try:
            severity_escalated = False
            if loc.last_alerted_at:
                time_since_last_alert = now - loc.last_alerted_at
                if time_since_last_alert < timedelta(minutes=ALERT_COOLDOWN_MINUTES):
                    try:
                        mock_state_pre = await repo.get_mock_state(loc.chat_id)
                        pre_result = await weather_manager.predict_rain(loc.latitude, loc.longitude, mock_state=mock_state_pre, location_name=loc.name)
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
                            return None
                    except Exception as e:
                        logger.warning(f"Smart Cooldown pre-check failed for {loc.chat_id}: {e}. Skipping.")
                        return None

            if not severity_escalated:
                mock_state = await repo.get_mock_state(loc.chat_id)
                result = await weather_manager.predict_rain(loc.latitude, loc.longitude, mock_state=mock_state, location_name=loc.name)

            max_rain = result.get("max_rain", 0.0)
            if max_rain < RAIN_TRIGGER_THRESHOLD_MM:
                if loc.last_alert_max_rain and loc.last_alert_max_rain > 0.0:
                    logger.info(f"Sending All-Clear alert for chat_id {loc.chat_id}")
                    loc_name_str = f" '{loc.name.capitalize()}' " if loc.name and loc.name.lower() != "default" else ""
                    text = f"☀️ สภาพอากาศ ณ พิกัด{loc_name_str}เคลียร์แล้ว\n(ไม่มีแนวโน้มฝนตกในขณะนี้)"
                    return {
                        "loc": loc,
                        "type": "all_clear",
                        "text": text,
                        "max_rain": 0.0,
                        "result": result
                    }
                else:
                    logger.debug(f"Skipping alert for {loc.chat_id}: Max rain {max_rain} mm/hr < threshold {RAIN_TRIGGER_THRESHOLD_MM}")
                return None

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
                
                loc_name_str = f" '{loc.name.capitalize()}' " if loc.name and loc.name.lower() != "default" else ""
                
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

                rain_summary = result.get("rain_summary")
                if rain_summary:
                    text += f"🌧️ ข้อมูลพยากรณ์ฝนสำหรับพิกัด{loc_name_str}ของคุณ\n"
                    text += f"{rain_summary}\n\n"
                    wind_dir_text = result.get("wind_dir_text", "ไม่ทราบ")
                    if wind_speed_kmh > 0: text += f"🌬️ สภาพลม: {wind_speed_kmh:.1f} km/h (พัดไปทางทิศ {wind_dir_text})\n"
                    if eta_minutes is not None and eta_minutes > 0 and wind_speed_kmh > 0: text += f"📏 ระยะห่างจากกลุ่มฝน: ประมาณ {distance_km:.1f} กม.\n"
                else:
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
                    if eta_minutes is not None and eta_minutes > 0 and wind_speed_kmh > 0: text += f"📏 ระยะห่างจากกลุ่มฝน: ประมาณ {distance_km:.1f} กม.\n"

                growth_rate = result.get("growth_rate_pct")
                if growth_rate is not None and "ไม่พบฝน" not in (rain_summary or ""):
                    if growth_rate > 5.0:
                        text += f"📈 พัฒนาการเมฆฝน (15 นาทีที่ผ่านมา): กำลังก่อตัวแรงขึ้น (+{growth_rate:.1f}%/15min)\n"
                    elif growth_rate < -5.0:
                        text += f"📉 พัฒนาการเมฆฝน (15 นาทีที่ผ่านมา): อ่อนกำลังลง ({growth_rate:.1f}%/15min)\n"
                    else:
                        text += f"➖ พัฒนาการเมฆฝน (15 นาทีที่ผ่านมา): คงที่\n"
                        
                text += f"📡 แหล่งข้อมูล: {source_name}\n"
                bkk_tz_now = timezone(timedelta(hours=7))
                update_time_str = datetime.now(bkk_tz_now).strftime("%d/%m/%Y %H:%M:%S")
                text += f"🔄 ข้อมูลอัปเดตล่าสุด: {update_time_str}\n"

                advanced_data = None
                try:
                    mock_state = await repo.get_mock_state(loc.chat_id)
                    advanced_data = await weather_manager.get_advanced_alerts(loc.latitude, loc.longitude, mock_state=mock_state)
                except Exception as e:
                    logger.error(f"Failed to get advanced alerts: {e}")

                return {
                    "loc": loc,
                    "type": "rain",
                    "text": text,
                    "max_rain": max_rain,
                    "result": result,
                    "advanced_data": advanced_data
                }

            return None
        except Exception as e:
            logger.error(f"Failed to evaluate location {loc.name} for chat_id {loc.chat_id}: {e}")
            return {"loc": loc, "type": "error", "error": str(e)}


async def _send_combined_alerts(chat_id, eval_results, repo, now):
    alerts_sent = 0
    errors = 0

    valid_results = [r for r in eval_results if r and r.get("type") != "error"]
    error_results = [r for r in eval_results if r and r.get("type") == "error"]
    errors += len(error_results)

    if not valid_results:
        return 0, errors

    combined_text_parts = []
    
    primary_loc = valid_results[0]["loc"]
    platform = getattr(primary_loc, "platform", "telegram") or "telegram"
    notifier = get_notification_service(platform)

    is_dev = str(chat_id) in DEVELOPER_CHAT_IDS
    reply_markup = get_radar_inline_keyboard(primary_loc.latitude, primary_loc.longitude, is_developer=is_dev)
    
    for r in valid_results:
        combined_text_parts.append(r["text"])
        
        loc = r["loc"]
        loc_name = loc.name.capitalize() if loc.name and loc.name.lower() != "default" else "Default"
        r_lat = round(loc.latitude, 4)
        r_lng = round(loc.longitude, 4)
        
        # 1 button row for radar comparisons / false alarms
        row = []
        row.append({"text": f"📊 เทียบ {loc_name}", "callback_data": f"compare_api_{r_lat}_{r_lng}"})
        
        if r["type"] == "rain":
            result = r["result"]
            max_rain = r["max_rain"]
            ep_map = {"tomorrow": "t", "rainbow-local": "rl", "rainbow-global": "rg", "xweather": "xw", "open-meteo": "om"}
            ep_code = ep_map.get(result.get("endpoint"), "u")
            cb_data = f"fb_falsealarm_{r_lat}_{r_lng}_{ep_code}_{max_rain:.1f}"
            row.append({"text": f"❌ ผิดพลาด {loc_name}", "callback_data": cb_data})
            
        reply_markup["inline_keyboard"].append(row)

    combined_text = "\n" + "─" * 20 + "\n\n"
    combined_text = combined_text.join(combined_text_parts)

    try:
        if platform == "telegram":
            await send_telegram_message(int(chat_id), combined_text, reply_markup=reply_markup)
        else:
            await notifier.send_text_message(str(chat_id), combined_text, reply_markup=reply_markup)
        alerts_sent += 1
    except Exception as e:
        logger.error(f"Failed to send combined text alert for chat_id {chat_id} on {platform}: {e}")
        return 0, errors + 1

    # Only send media files (radar photos, timelines, gifs) on Telegram to save LINE push quota
    for r in valid_results:
        if r["type"] == "rain":
            loc = r["loc"]
            result = r["result"]
            
            gif_bytes = result.get("radar_gif_bytes")
            static_bytes = result.get("radar_static_bytes")
            tracking_bytes = result.get("radar_tracking_bytes")
            timeline_bytes = result.get("rain_timeline_bytes")
            multiframe_bytes = result.get("radar_multiframe_bytes")
            
            is_dev = os.getenv("ENVIRONMENT", "production").lower() == "development"
            
            if platform == "telegram":
                try:
                    chat_id_val = int(chat_id)
                    if tracking_bytes:
                        await send_telegram_photo(chat_id_val, tracking_bytes, f"radar_tracking_{loc.name}.png")
                    
                    # Send additional detail images on Dev server to save Production traffic
                    if is_dev:
                        if static_bytes: await send_telegram_photo(chat_id_val, static_bytes, f"radar_latest_{loc.name}.png")
                        if timeline_bytes: await send_telegram_photo(chat_id_val, timeline_bytes, f"rain_timeline_{loc.name}.png")
                        if multiframe_bytes: await send_telegram_photo(chat_id_val, multiframe_bytes, f"radar_multiframe_{loc.name}.png")
                        if gif_bytes: await send_telegram_document(chat_id_val, gif_bytes, f"radar_nowcast_{loc.name}.gif")
                except Exception as e:
                    logger.error(f"Failed to send images for {loc.name} of chat_id {chat_id} on {platform}: {e}")
                    errors += 1
            
            try:
                await repo.update_last_alerted(loc, now, max_rain=r["max_rain"])
            except Exception as e:
                logger.error(f"Failed to update db for {loc.name}: {e}")
                errors += 1
        elif r["type"] == "all_clear":
            loc = r["loc"]
            try:
                await repo.update_last_alerted(loc, now, max_rain=0.0)
            except Exception as e:
                logger.error(f"Failed to update db for all-clear: {e}")
                errors += 1

    # Only send advanced alerts (lightning, storm cells) on Telegram to save LINE push quota
    if platform == "telegram":
        for r in valid_results:
            if r["type"] == "rain" and r.get("advanced_data"):
                loc = r["loc"]
                advanced_data = r["advanced_data"]
                has_advisory = len(advanced_data.get("advisories", [])) > 0
                has_lightning = advanced_data.get("lightning") is not None
                has_stormcell = advanced_data.get("stormcell") is not None
                
                if has_advisory or has_lightning or has_stormcell:
                    loc_name_str = f"สำหรับพิกัด '{loc.name.capitalize()}' " if loc.name and loc.name.lower() != "default" else ""
                    adv_text = f"🚨 *ข้อมูลเตือนภัยขั้นสูงรอบตัวคุณ {loc_name_str}*\n\n"
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
                    
                    try:
                        await send_telegram_message(int(chat_id), adv_text)
                    except Exception as e:
                        logger.error(f"Failed to send advanced alert for {loc.name} on {platform}: {e}")
                        errors += 1

    return alerts_sent, errors


async def _process_location(loc, repo, weather_manager, now, sem):
    eval_res = await _evaluate_location(loc, repo, weather_manager, now, sem)
    if not eval_res:
        return 0, 0
    return await _send_combined_alerts(loc.chat_id, [eval_res], repo, now)


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
        
        async def _process_with_stagger(loc, idx):
            await asyncio.sleep(idx * 0.5)
            return await _process_location(loc, repo, weather_manager, now, sem)
            
        tasks = [_process_with_stagger(loc, idx) for idx, loc in enumerate(target_locs)]
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

        # Issue #122: Group locations by chat_id to prevent triple alert spam
        chat_groups = {}
        for loc in locations:
            chat_groups.setdefault(loc.chat_id, []).append(loc)

        # Issue #123: Reduce concurrency and add stagger
        sem = asyncio.Semaphore(5)
        
        async def _process_chat_group(chat_id, locs, stagger_idx):
            await asyncio.sleep(stagger_idx * 0.5)
            
            # Evaluate all user locations
            eval_results = []
            for loc in locs:
                eval_res = await _evaluate_location(loc, repo, weather_manager, now, sem)
                if eval_res:
                    eval_results.append(eval_res)
                    
            if not eval_results:
                return 0, 0
                
            # Send them combined
            return await _send_combined_alerts(chat_id, eval_results, repo, now)

        tasks = [_process_chat_group(chat_id, locs, idx) for idx, (chat_id, locs) in enumerate(chat_groups.items())]
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
        try:
            processor = TMDRadarProcessor(station_code=station)
            return await processor.update_radar_cache(force=False)
        except Exception as e:
            logger.error(f"Failed to cache TMD radar for {station}: {e}")
            return {"station": station, "updated": False, "error": str(e)}

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
