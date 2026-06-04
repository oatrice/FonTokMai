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
                        
                    is_dev = str(loc.chat_id) in DEVELOPER_CHAT_IDS
                    reply_markup = get_radar_inline_keyboard(loc.latitude, loc.longitude, is_developer=is_dev)
                    
                    logger.info(f"Alerting chat_id {loc.chat_id}: ETA {eta_minutes} mins")
                    
                    # Call Telegram Service
                    await send_telegram_message(loc.chat_id, text, reply_markup=reply_markup)
                    
                    # Update DB (บันทึกทั้งเวลาและความรุนแรงของฝน)
                    await repo.update_last_alerted(loc, now, max_rain=max_rain)
                    
            except Exception as e:
                logger.error(f"Failed to check rain for chat_id {loc.chat_id}: {e}")
