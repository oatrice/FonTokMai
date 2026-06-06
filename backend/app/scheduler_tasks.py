import os
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from app.dependencies import get_repo_context
from app.services.weather_manager import WeatherManager
from app.services.telegram import send_telegram_message, get_radar_inline_keyboard, DEVELOPER_CHAT_IDS

logger = logging.getLogger(__name__)

# Minimum cooldown between alerts in minutes
ALERT_COOLDOWN_MINUTES = int(os.getenv("ALERT_COOLDOWN_MINUTES", "120"))
RAIN_TRIGGER_THRESHOLD_MM = float(os.getenv("RAIN_TRIGGER_THRESHOLD_MM", "0.5"))

# Use Thailand timezone for display
BKK_TZ = ZoneInfo("Asia/Bangkok")

async def check_rain_and_alert():
    """
    Background job to check rain for all active locations and alert users.
    """
    logger.info("Starting proactive rain check...")
    
    async with get_repo_context() as repo:
        locations = await repo.get_active_locations()
        
        if not locations:
            logger.info("No active locations to check.")
            return

        weather_manager = WeatherManager()
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        for loc in locations:
            # --- Smart Cooldown (Issue #26) ---
            severity_escalated = False
            if loc.last_alerted_at:
                time_since_last_alert = now - loc.last_alerted_at
                if time_since_last_alert < timedelta(minutes=ALERT_COOLDOWN_MINUTES):
                    # ยังอยู่ใน cooldown window → ดึงข้อมูลก่อนเพื่อตรวจสอบความรุนแรง
                    try:
                        mock_state_pre = await repo.get_mock_state(loc.chat_id)
                        pre_result = await weather_manager.predict_rain(loc.latitude, loc.longitude, mock_state=mock_state_pre)
                        current_max_rain = pre_result.get("max_rain", 0.0)
                        last_max_rain = loc.last_alert_max_rain or 0.0

                        if current_max_rain > last_max_rain and current_max_rain >= RAIN_TRIGGER_THRESHOLD_MM:
                            # ความรุนแรงเพิ่มขึ้น → ทะลุบล็อก และใช้ผลลัพธ์ที่ดึงมาแล้ว
                            logger.info(
                                f"Smart Cooldown override for chat_id {loc.chat_id}: "
                                f"rain {last_max_rain:.1f} → {current_max_rain:.1f} mm/hr"
                            )
                            severity_escalated = True
                            result = pre_result
                        elif last_max_rain > 0.0 and current_max_rain < RAIN_TRIGGER_THRESHOLD_MM:
                            # All-Clear condition met during cooldown → ทะลุบล็อกส่ง All-Clear
                            logger.info(f"Smart Cooldown override (All-Clear) for chat_id {loc.chat_id}")
                            result = pre_result
                        else:
                            logger.debug(
                                f"Skipping chat_id {loc.chat_id} (cooldown, "
                                f"rain {current_max_rain:.1f} mm/hr ≤ last {last_max_rain:.1f} mm/hr)"
                            )
                            continue
                    except Exception as e:
                        logger.warning(f"Smart Cooldown pre-check failed for {loc.chat_id}: {e}. Skipping.")
                        continue

            try:
                # ถ้า severity_escalated จะมี result อยู่แล้วจาก pre-check ของ Smart Cooldown
                if not severity_escalated:
                    mock_state = await repo.get_mock_state(loc.chat_id)
                    result = await weather_manager.predict_rain(loc.latitude, loc.longitude, mock_state=mock_state)

                # Filter by Threshold
                max_rain = result.get("max_rain", 0.0)
                if max_rain < RAIN_TRIGGER_THRESHOLD_MM:
                    # All-Clear Logic (Issue #41)
                    if loc.last_alert_max_rain and loc.last_alert_max_rain > 0.0:
                        logger.info(f"Sending All-Clear alert for chat_id {loc.chat_id}")
                        loc_name_str = f" '{loc.name.capitalize()}' " if loc.name and loc.name.lower() != "default" else " "
                        text = f"☀️ สภาพอากาศ ณ พิกัด{loc_name_str}เคลียร์แล้ว\n(ไม่มีแนวโน้มฝนตกในขณะนี้)"
                        await send_telegram_message(loc.chat_id, text)
                        await repo.update_last_alerted(loc, now, max_rain=0.0)
                    else:
                        logger.debug(f"Skipping alert for {loc.chat_id}: Max rain {max_rain} mm/hr < threshold {RAIN_TRIGGER_THRESHOLD_MM}")
                    continue
                
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
                                    eta_minutes = int((pred_time - base_time).total_seconds() / 60)
                                    rain_start_dt = pred_time
                                except Exception:
                                    eta_minutes = 0
                            else:
                                eta_minutes = 0
                            break
                
                # We only alert proactively if rain is coming within 60 mins
                if eta_minutes is not None and eta_minutes <= 60:
                    intensity_str = result.get("intensity", "ไม่ทราบ")
                    duration_min = result.get("duration_minutes", 0)
                    wind_speed_kmh = result.get("wind_speed_kmh", 0.0)
                    endpoint_source = result.get("endpoint", "unknown")
                    
                    # Convert endpoints to human-readable format
                    source_name = endpoint_source
                    if endpoint_source == "tomorrow":
                        source_name = "Tomorrow.io"
                    elif endpoint_source == "rainbow-local":
                        source_name = "Rainbow (Local)"
                    elif endpoint_source == "rainbow-global":
                        source_name = "Rainbow (Global)"
                    
                    loc_name_str = f" '{loc.name.capitalize()}' " if loc.name and loc.name.lower() != "default" else " "
                    
                    # Formatting Times
                    if not rain_start_dt:
                        rain_start_dt = datetime.now(timezone.utc) + timedelta(minutes=eta_minutes)
                        
                    rain_end_dt = rain_start_dt + timedelta(minutes=duration_min)
                    
                    start_time_str = rain_start_dt.astimezone(BKK_TZ).strftime("%H:%M น.")
                    end_time_str = rain_end_dt.astimezone(BKK_TZ).strftime("%H:%M น.")
                    
                    # Calculate Distance
                    # distance = (time in hours) * speed
                    distance_km = (eta_minutes / 60.0) * wind_speed_kmh
                    
                    # เพิ่มส่วนหัวพิเศษเมื่อ Smart Cooldown ทะลุบล็อก
                    if severity_escalated:
                        last_rain_val = loc.last_alert_max_rain or 0.0
                        text = (
                            f"⚠️ *อัปเดต: ฝนทวีความรุนแรงขึ้น!*\n"
                            f"({last_rain_val:.1f} mm/hr → {max_rain:.1f} mm/hr)\n\n"
                        )
                    else:
                        text = ""

                    if eta_minutes == 0:
                        text += f"🌧️ ฝนกำลังตกอยู่ที่พิกัด{loc_name_str}ของคุณ ณ ขณะนี้\n"
                    else:
                        text += f"🌧️ ฝนกำลังเคลื่อนมาทางพิกัด{loc_name_str}ของคุณ\n"
                        text += f"⏰ จะเริ่มตกเวลา: {start_time_str} (ในอีก {eta_minutes} นาที)\n"
                    
                    # Duration/End time
                    duration_text = f"ตกต่อเนื่อง {duration_min} นาที"
                    if duration_min >= 60:
                        hrs = duration_min // 60
                        mins = duration_min % 60
                        if mins > 0:
                            duration_text = f"ตกต่อเนื่อง {hrs} ชม. {mins} นาที"
                        else:
                            duration_text = f"ตกต่อเนื่อง {hrs} ชม."
                        
                    if duration_min > 0:
                        text += f"🛑 คาดว่าจะหยุดเวลา: {end_time_str} ({duration_text})\n\n"
                    else:
                        text += "\n"
                        
                    text += f"💧 ความรุนแรง: {intensity_str} ({max_rain:.1f} mm/hr)\n"
                    
                    if wind_speed_kmh > 0:
                        text += f"🌬️ สภาพลม: {wind_speed_kmh:.1f} km/h\n"
                        
                    if eta_minutes > 0 and wind_speed_kmh > 0:
                        text += f"📏 ระยะห่างจากกลุ่มฝน: ประมาณ {distance_km:.1f} กม.\n"
                        
                    text += f"📡 แหล่งข้อมูล: {source_name}\n"
                    
                    # Add Last Updated Time
                    bkk_tz = timezone(timedelta(hours=7))
                    update_time_str = datetime.now(bkk_tz).strftime("%d/%m/%Y %H:%M:%S")
                    text += f"🔄 ข้อมูลอัปเดตล่าสุด: {update_time_str}\n"
                        
                    is_dev = str(loc.chat_id) in DEVELOPER_CHAT_IDS
                    reply_markup = get_radar_inline_keyboard(loc.latitude, loc.longitude, is_developer=is_dev)
                    
                    # Append Issue #39 and #42 Buttons
                    r_lat = round(loc.latitude, 4)
                    r_lng = round(loc.longitude, 4)
                    reply_markup["inline_keyboard"].append([
                        {"text": "📊 เทียบข้อมูล", "callback_data": f"compare_api_{r_lat}_{r_lng}"}
                    ])
                    
                    ep_map = {"tomorrow": "t", "rainbow-local": "rl", "rainbow-global": "rg", "xweather": "xw", "open-meteo": "om"}
                    ep_code = ep_map.get(result.get("endpoint"), "u")
                    cb_data = f"fb_falsealarm_{r_lat}_{r_lng}_{ep_code}_{max_rain:.1f}"
                    
                    reply_markup["inline_keyboard"].append([
                        {"text": "❌ แจ้งเตือนผิดพลาด (ฝนไม่ตกจริง)", "callback_data": cb_data}
                    ])
                    
                    logger.info(f"Alerting chat_id {loc.chat_id}: ETA {eta_minutes} mins")
                    
                    # Call Telegram Service
                    await send_telegram_message(loc.chat_id, text, reply_markup=reply_markup)
                    
                    # Update DB (บันทึกทั้งเวลาและความรุนแรงของฝน)
                    await repo.update_last_alerted(loc, now, max_rain=max_rain)
                    
                    # --- Advanced Alerts (Issue #33-35) ---
                    try:
                        advanced_data = await weather_manager.get_advanced_alerts(loc.latitude, loc.longitude, mock_state=mock_state)
                        has_advisory = len(advanced_data.get("advisories", [])) > 0
                        has_lightning = advanced_data.get("lightning") is not None
                        has_stormcell = advanced_data.get("stormcell") is not None
                        
                        if has_advisory or has_lightning or has_stormcell:
                            adv_text = "🚨 *ข้อมูลเตือนภัยขั้นสูงรอบตัวคุณ*\n\n"
                            
                            if has_advisory:
                                for adv in advanced_data["advisories"]:
                                    adv_text += f"⚠️ ประกาศเตือนภัย: {adv.get('name', '')}\n"
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
                            
                            # Send secondary message box
                            await send_telegram_message(loc.chat_id, adv_text)
                    except Exception as e:
                        logger.error(f"Failed to process advanced alerts for {loc.chat_id}: {e}")
                    
            except Exception as e:
                logger.error(f"Failed to check rain for chat_id {loc.chat_id}: {e}")

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
    """Run frequently (e.g., every 15 mins) to fetch and cache TMD Radar images."""
    logger.info("Starting TMD Radar fetch routine...")
    from app.services.tmd_radar_processor import TMDRadarProcessor
    
    stations_to_update = ["kkn120", "kkn240", "skn240"]
    for station in stations_to_update:
        try:
            processor = TMDRadarProcessor(station_code=station)
            latest_bytes = await processor.fetch_latest_image_bytes()
            if latest_bytes:
                logger.info(f"Successfully fetched latest radar image for {station} (Size: {len(latest_bytes)} bytes)")
                saved_filename = await processor.save_polled_frame(latest_bytes)
                logger.info(f"Saved radar frame to {saved_filename}")
                
                deleted = await processor.cleanup_old_frames(max_age_hours=3)
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} old frames for {station}")
        except Exception as e:
            logger.error(f"Failed to fetch TMD radar for {station}: {e}")

