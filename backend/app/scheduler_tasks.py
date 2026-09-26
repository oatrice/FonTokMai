import os
import time
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from app.dependencies import get_repo_context
from app.services.weather_manager import WeatherManager
from app.services.alert_formatter import AlertDecision, TelegramFormatter
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

async def _evaluate_location(loc, mock_states, weather_manager, now, sem):
    async with sem:
        try:
            severity_escalated = False
            if loc.last_alerted_at:
                time_since_last_alert = now - loc.last_alerted_at
                if time_since_last_alert < timedelta(minutes=ALERT_COOLDOWN_MINUTES):
                    try:
                        mock_state_pre = mock_states.get(loc.chat_id)
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
                mock_state = mock_states.get(loc.chat_id)
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
                
                decision = AlertDecision(
                    location_name=loc.name,
                    type="rain",
                    max_rain=max_rain,
                    result=result,
                    severity_escalated=severity_escalated,
                    last_max_rain=loc.last_alert_max_rain or 0.0
                )
                text = TelegramFormatter.format(decision)
    

                advanced_data = None
                try:
                    mock_state = mock_states.get(loc.chat_id)
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


async def _send_combined_alerts(chat_id, eval_results, now, is_mock: bool = False):
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
        # Check presence policy and cached answers for rain alerts (Issue #291)
        rain_alerts = [r for r in valid_results if r["type"] == "rain"]
        send_full_alert = True

        if rain_alerts and platform == "telegram":
            for r in rain_alerts:
                loc = r["loc"]
                policy = getattr(loc, "presence_policy", "always_ask")
                loc_name = loc.name or "default"

                if policy == "always_notify":
                    continue

                if policy == "silent_card":
                    # Send silent notification without sound
                    await send_telegram_message(int(chat_id), combined_text, reply_markup=reply_markup, disable_notification=True)
                    send_full_alert = False
                    break

                if policy == "schedule_based":
                    # Check schedule window
                    import json
                    bkk_now = datetime.now(BKK_TZ)
                    current_weekday = bkk_now.isoweekday() # 1=Mon .. 7=Sun
                    current_time_str = bkk_now.strftime("%H:%M")
                    
                    in_schedule = True
                    if loc.schedule_active_days:
                        try:
                            active_days = json.loads(loc.schedule_active_days)
                            if current_weekday not in active_days:
                                in_schedule = False
                        except Exception:
                            pass
                    if in_schedule and loc.schedule_active_start and loc.schedule_active_end:
                        if not (loc.schedule_active_start <= current_time_str <= loc.schedule_active_end):
                            in_schedule = False

                    if in_schedule:
                        continue # Inside window -> send full alert directly

                # For 'always_ask' or outside 'schedule_based' window: check cache
                async with get_repo_context() as repo:
                    cached_answer = await repo.get_presence_answer(chat_id, loc_name)
                    if cached_answer == "yes":
                        continue # User confirmed presence previously
                    elif cached_answer == "no":
                        logger.info(f"Skipping alert for {chat_id} at {loc_name} due to cached 'no' presence answer.")
                        return 0, errors
                    else:
                        # Cache MISS -> Send Presence Ping with Countdown and inline actions
                        eta_min = r.get("result", {}).get("eta_minutes", 20)
                        max_r = r.get("max_rain", 1.0)
                        ping_text = (
                            f"🌧️ **ตรวจพบกลุ่มฝนใกล้พิกัด [{loc_name}]**\n\n"
                            f"• ความรุนแรง: `{max_r:.1f} mm/hr`\n"
                            f"• คาดว่าจะเริ่มตกในอีก: `{eta_min}` นาที\n\n"
                            f"ตอนนี้คุณอยู่ที่นี่และต้องการรับการแจ้งเตือนแบบเต็มรูปแบบไหมครับ?"
                        )
                        ping_keyboard = [
                            [
                                {"text": "✅ ใช่ ส่งข้อมูลเต็ม", "callback_data": f"presence_ans_{loc_name}_yes"},
                                {"text": "❌ ไม่ต้องส่ง", "callback_data": f"presence_ans_{loc_name}_no"}
                            ],
                            [
                                {"text": "🔕 ปิด 4 ชม.", "callback_data": f"loc_snooze_{loc_name}_4"},
                                {"text": "⚙️ ตั้งค่า", "callback_data": f"presence_menu_{loc_name}"}
                            ]
                        ]
                        await send_telegram_message(int(chat_id), ping_text, reply_markup={"inline_keyboard": ping_keyboard})
                        send_full_alert = False
                        break

        if send_full_alert:
            if platform == "telegram":
                await send_telegram_message(int(chat_id), combined_text, reply_markup=reply_markup)
            else:
                await notifier.send_text_message(str(chat_id), combined_text, reply_markup=reply_markup)
            alerts_sent += 1

            # Log to SystemUsageEvent for Accuracy & False Alarm Verification (Issue #292 & #298)
            try:
                from app.models import SystemUsageEvent
                async with get_repo_context() as repo:
                    if hasattr(repo, "session") and repo.session:
                        for r in valid_results:
                            loc = r["loc"]
                            log_entry = SystemUsageEvent(
                                chat_id=str(chat_id),
                                location_name=loc.name or "default",
                                latitude=loc.latitude,
                                longitude=loc.longitude,
                                alerted_at=now.replace(tzinfo=None),
                                rain_intensity_mm=r.get("max_rain", 0.0),
                                alert_type=r.get("type", "rain"),
                                event_category="mock_test" if is_mock else "proactive_alert",
                                command_name="/mock_rain" if is_mock else "proactive_scheduler",
                                is_mock=is_mock
                            )
                            repo.session.add(log_entry)
                        await repo.session.commit()
            except Exception as e:
                logger.error(f"Failed to write to SystemUsageEvent: {e}")
        else:
            return 1, errors

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
                async with get_repo_context() as session_repo:
                    await session_repo.update_last_alerted(loc, now, max_rain=r["max_rain"])
            except Exception as e:
                logger.error(f"Failed to update db for {loc.name}: {e}")
                errors += 1
        elif r["type"] == "all_clear":
            loc = r["loc"]
            try:
                async with get_repo_context() as session_repo:
                    await session_repo.update_last_alerted(loc, now, max_rain=0.0)
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


async def _process_location(loc, mock_states, weather_manager, now, sem):
    eval_res = await _evaluate_location(loc, mock_states, weather_manager, now, sem)
    if not eval_res:
        return 0, 0
    return await _send_combined_alerts(loc.chat_id, [eval_res], now)


async def run_alert_for_locations(target_locs: list):
    """Run the rain check and alert pipeline for a specific list of locations only.
    Used by /devmock scenario loc:name to fire an alert for a single saved location
    without triggering the full scheduler sweep.
    """
    try:
        async with get_repo_context() as repo:
            mock_states = {}
            for loc in target_locs:
                if loc.chat_id not in mock_states:
                    mock_states[loc.chat_id] = await repo.get_mock_state(loc.chat_id)
    except Exception as e:
        logger.error(f"[run_alert_for_locations] Mock states fetch error: {e}")
        return

    weather_manager = WeatherManager()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    sem = asyncio.Semaphore(5)
    
    async def _process_with_stagger(loc, idx):
        await asyncio.sleep(idx * 0.5)
        return await _process_location(loc, mock_states, weather_manager, now, sem)
        
    tasks = [_process_with_stagger(loc, idx) for idx, loc in enumerate(target_locs)]
    await asyncio.gather(*tasks, return_exceptions=True)


async def check_rain_and_alert():
    logger.info("Starting proactive rain check...")
    start_time = time.time()
    alerts_sent = 0
    errors = 0
    
    try:
        async with get_repo_context() as repo:
            locations = await repo.get_active_locations()
            if not locations:
                logger.info("No active locations to check.")
                return
            
            mock_states = {}
            for loc in locations:
                if loc.chat_id not in mock_states:
                    mock_states[loc.chat_id] = await repo.get_mock_state(loc.chat_id)
    except Exception as e:
        logger.error(f"Error fetching locations/mock states from DB: {e}")
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
            eval_res = await _evaluate_location(loc, mock_states, weather_manager, now, sem)
            if eval_res:
                eval_results.append(eval_res)
                
        if not eval_results:
            return 0, 0
            
        # Send them combined
        return await _send_combined_alerts(chat_id, eval_results, now)

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
        async with get_repo_context() as repo:
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
    from app.database import AsyncSessionLocal
    from app.services.tmd_radar_registry import radar_registry
    import httpx
    import asyncio

    # Dynamically load all active stations from Neon DB (or registry fallback)
    async with AsyncSessionLocal() as session:
        active_stations_map = await radar_registry.get_all_stations(session)
        stations_to_update = list(active_stations_map.keys())

    if not stations_to_update:
        stations_to_update = ["kkn240", "skn240", "tak", "cri", "chn", "cmp", "hyi", "phs", "ryg", "srt", "svp240", "ubn240"]

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


async def update_daily_burn_rate_routine():
    """Daily cron job to fetch actual GCP costs and sync burn_rate_per_day to system_config."""
    logger.info("Starting daily GCP burn rate sync routine...")
    from app.services import gcp_billing
    from app.database import AsyncSessionLocal
    from app.models import SystemConfig
    from sqlalchemy.future import select
    import json
    from decimal import Decimal, ROUND_HALF_UP

    try:
        billing_svc = gcp_billing.GCPBillingService()
        cost_breakdown = billing_svc.get_current_month_costs(
            period="current_month",
            require_real_data=True,
        )

        if cost_breakdown.is_mock:
            raise RuntimeError(
                "GCP burn rate sync received mock billing data; "
                "check BigQuery credentials and billing dataset configuration."
            )
        
        # Calculate daily burn rate from month-to-date total or mock
        # If period_start is YYYY-MM-01, calculate days elapsed so far
        now = datetime.now(timezone.utc)
        day_of_month = max(1, now.day)

        # Daily burn rate = MTD Total THB / days elapsed
        total_thb = Decimal(str(cost_breakdown.total_thb))
        daily_burn_thb = (total_thb / Decimal(day_of_month)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        
        # Minimum baseline floor (e.g. 5.0 THB/day for fixed storage/IP costs)
        MINIMUM_DAILY_BURN_THB = 5.0
        daily_burn_thb = float(daily_burn_thb)
        daily_burn_thb = max(daily_burn_thb, MINIMUM_DAILY_BURN_THB)

        logger.info(
            "[GCP_BILLING_SYNC] Fetched burn data: "
            f"is_mock={cost_breakdown.is_mock}, "
            f"period={cost_breakdown.period_start}..{cost_breakdown.period_end}, "
            f"total_thb={cost_breakdown.total_thb:.2f}, "
            f"days_elapsed={day_of_month}, "
            f"daily_burn_thb={daily_burn_thb:.2f}"
        )

        async with AsyncSessionLocal() as session:
            stmt = select(SystemConfig).where(SystemConfig.key == "burn_rate_per_day")
            res = await session.execute(stmt)
            config = res.scalar_one_or_none()
            
            if config:
                config.value_json = json.dumps(daily_burn_thb)
            else:
                session.add(SystemConfig(key="burn_rate_per_day", value_json=json.dumps(daily_burn_thb)))
            
            await session.commit()
            logger.info(f"[GCP_BILLING_SYNC] Synced burn_rate_per_day to {daily_burn_thb} THB/day (MTD total ${cost_breakdown.total_usd:.2f})")
            return {
                "daily_burn_thb": daily_burn_thb,
                "total_thb": float(total_thb),
                "days_elapsed": day_of_month,
                "period_start": cost_breakdown.period_start,
                "period_end": cost_breakdown.period_end,
                "is_mock": cost_breakdown.is_mock,
            }
    except Exception as e:
        logger.error(f"[GCP_BILLING_SYNC] Failed to sync daily burn rate: {e}", exc_info=True)
        raise  # Re-raise so worker endpoint can surface the actual error


async def sync_gcp_billing_history_routine():
    """
    Monthly GCP Billing History Archiver (Issue #249, #339):
    Runs periodically (e.g. on the 6th of each month) to proactively freeze and archive
    the previous month's finalized GCP billing data into the PostgreSQL database.
    """
    from app.services import gcp_billing

    now = datetime.now(timezone.utc)

    # Compute last month YYYY-MM
    first_of_this_month = now.date().replace(day=1)
    last_day_of_last_month = first_of_this_month - timedelta(days=1)
    last_month_str = last_day_of_last_month.strftime("%Y-%m")

    logger.info("[GCP_BILLING_ARCHIVE] Checking archive for last_month=%s (current_day=%d)", last_month_str, now.day)

    billing_svc = gcp_billing.GCPBillingService()
    # Force refresh ensures we fetch the finalized numbers from BigQuery and persist to DB
    breakdown = await billing_svc.get_costs_with_archive(
        period=last_month_str,
        force_refresh=True,
    )

    logger.info(
        "[GCP_BILLING_ARCHIVE] Synced historical billing for %s: total_thb=%.2f is_mock=%s",
        last_month_str,
        breakdown.total_thb,
        breakdown.is_mock,
    )
    return {
        "status": "success",
        "month": last_month_str,
        "total_thb": breakdown.total_thb,
        "is_mock": breakdown.is_mock,
    }



async def auto_verify_false_alarms_routine():
    """
    Auto-Verification Worker (Issue #292):
    Runs periodically to check alerts sent between 30 and 90 minutes ago
    that do not yet have an auto_verify_result. Re-predicts rain intensity;
    if max_rain <= 0.0 mm/hr, marks as 'false_alarm', otherwise 'true_alarm'.
    """
    logger.info("Starting auto-verify false alarms routine...")
    from app.database import AsyncSessionLocal
    from app.models import SystemUsageEvent
    from sqlalchemy.future import select
    from app.services.weather_manager import WeatherManager
    from app.services.alert_formatter import AlertDecision, TelegramFormatter

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    min_time = now - timedelta(minutes=90)
    max_time = now - timedelta(minutes=30)

    verified_count = 0
    wm = WeatherManager()

    try:
        async with AsyncSessionLocal() as session:
            stmt = select(SystemUsageEvent).where(
                SystemUsageEvent.auto_verify_result.is_(None),
                SystemUsageEvent.alerted_at >= min_time,
                SystemUsageEvent.alerted_at <= max_time
            )
            res = await session.execute(stmt)
            unverified_logs = res.scalars().all()

            for entry in unverified_logs:
                try:
                    result = await wm.predict_rain(entry.latitude, entry.longitude, location_name=entry.location_name)
                    actual_rain = result.get("max_rain", 0.0)
                    entry.auto_verified_at = now
                    if actual_rain <= 0.0:
                        entry.auto_verify_result = "false_alarm"
                    else:
                        entry.auto_verify_result = "true_alarm"
                    verified_count += 1
                except Exception as ex:
                    logger.warning(f"Failed to auto-verify alert log #{entry.id}: {ex}")

            await session.commit()
            logger.info(f"Auto-verify routine completed: verified {verified_count} alert logs.")
            return {"status": "ok", "verified_count": verified_count}
    except Exception as e:
        logger.error(f"Error in auto_verify_false_alarms_routine: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}

