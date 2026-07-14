from fastapi import APIRouter, Request, BackgroundTasks
import httpx
import os
import logging
from datetime import datetime, timezone
from app.services.weather_manager import WeatherManager
from app.dependencies import get_repo_context
from app.services.telegram import (
    send_telegram_message,
    send_telegram_message_return_id,
    edit_telegram_message,
    answer_callback_query,
    get_radar_inline_keyboard,
    send_telegram_document,
    DEVELOPER_CHAT_IDS,
)
import json

logger = logging.getLogger(__name__)

LAST_ACTIVE_LOCATION: dict[int, str] = {}

# Most recently pinned/sent Telegram location per chat (lat, lng).
# Populated whenever the user sends a location via Telegram, and consumed by
# /lock (and the inline lock button) when no saved-location name is supplied,
# so that locking targets the spot the user just shared instead of "home".
LAST_PINNED_LOCATION: dict[int, tuple[float, float]] = {}

router = APIRouter(
    prefix="/api/v1/telegram",
    tags=["webhook"]
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "mock_token")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
TELEGRAM_EDIT_REPLY_MARKUP_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageReplyMarkup"

def log_audit_event(event_type: str, chat_id: int, username: str, details: dict):
    audit_data = {
        "event_type": event_type,
        "chat_id": chat_id,
        "username": username or "unknown",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details
    }
    logger.info(json.dumps(audit_data, ensure_ascii=False))

async def check_admin_access(chat_id: int) -> bool:
    import os
    is_prod = os.getenv("ENVIRONMENT", "production").lower() != "development"

    async with get_repo_context() as repo:
        if await repo.has_active_admin_bypass(chat_id):
            return True
            
    # ถ้าอยู่ใน Development mode, Developer เข้าถึงได้เลยโดยไม่ต้อง bypass
    if str(chat_id) in DEVELOPER_CHAT_IDS and not is_prod:
        return True
        
    return False


def format_duration_text(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} นาที"
    hrs = minutes // 60
    mins = minutes % 60
    if mins > 0:
        return f"{hrs} ชม. {mins} นาที"
    return f"{hrs} ชม."


def _build_forecast_text(result: dict) -> str:
    """
    สร้างข้อความพยากรณ์ฝนจาก result dict ที่ได้จาก WeatherManager
    ใช้ร่วมกันทั้ง process_telegram_location และ handle_callback_query (raw data)
    """
    predictions = result.get("predictions", [])
    actual_endpoint = result.get("endpoint", "unknown")

    # แปลงชื่อ endpoint เป็นภาษามนุษย์
    endpoint_label_map = {
        "tomorrow": "Tomorrow.io",
        "rainbow-local": "Rainbow Local Radar",
        "rainbow-global": "Rainbow Global",
        "tmd-radar": "TMD Radar",
        "error": "ไม่สามารถเชื่อมต่อได้",
    }
    endpoint_label = endpoint_label_map.get(actual_endpoint, actual_endpoint)
    if actual_endpoint.startswith("tmd-radar (") and actual_endpoint.endswith(")"):
        endpoint_label = actual_endpoint.replace("tmd-radar", "TMD Radar", 1)

    # คำนวณ ETA
    eta_minutes = None
    if predictions:
        try:
            base_time = datetime.fromisoformat(predictions[0].get("time", "").replace("Z", "+00:00"))
        except Exception:
            base_time = None

        for pred in predictions:
            if pred.get("rain", 0) > 0:
                if base_time:
                    try:
                        pred_time = datetime.fromisoformat(pred.get("time", "").replace("Z", "+00:00"))
                        eta_minutes = int((pred_time - base_time).total_seconds() / 60)
                    except Exception:
                        eta_minutes = 0
                else:
                    eta_minutes = 0
                break

    if eta_minutes is not None or result.get("max_rain", 0) > 0 or result.get("rain_summary"):
        intensity_str = result.get("intensity", "ไม่ทราบ")
        duration_min = result.get("duration_minutes", 0)
        rain_summary = result.get("rain_summary")

        if rain_summary:
            text = f"🌧️ ข้อมูลพยากรณ์ฝน (ตรวจสอบด้วย: {endpoint_label})\n"
            text += f"{rain_summary}\n"
        else:
            if eta_minutes == 0 or (eta_minutes is None and result.get("max_rain", 0) > 0):
                text = f"🌧️ ฝนกำลังตกอยู่ที่พิกัดของคุณ ณ ขณะนี้ (ตรวจสอบด้วย: {endpoint_label})\n"
            else:
                text = f"🌧️ ฝนกำลังเคลื่อนมาทางทิศของคุณ จะเริ่มตกในอีก {format_duration_text(eta_minutes)} (ตรวจสอบด้วย: {endpoint_label})\n"
            
            if intensity_str == "ไม่มีฝน" and eta_minutes and eta_minutes > 0:
                text += f"💧 ความรุนแรง (คาดการณ์): ฝนกำลังจะมา\n"
            else:
                text += f"💧 ความรุนแรง: {intensity_str}\n"

            if duration_min > 0:
                text += f"⏱️ คาดว่าจะตกต่อเนื่องประมาณ: {format_duration_text(duration_min)}\n"
        
        has_rain_or_clouds = "ยังไม่มีแนวโน้มฝนตก" not in result.get("rain_summary", "") or "หมายเหตุ: ตรวจพบกลุ่มฝน" in result.get("rain_summary", "")
        
        wind_kmh = result.get("wind_speed_kmh", 0)
        wind_dir = result.get("wind_dir_text", "ไม่ทราบ")
        if wind_kmh > 0:
            if "tmd-radar" in actual_endpoint:
                if has_rain_or_clouds:
                    text += f"🌬️ ทิศที่พายุเคลื่อนที่ไป: {wind_kmh} km/h (ทิศ {wind_dir})\n"
            else:
                text += f"🌬️ สภาพลม: {wind_kmh} km/h (ทิศ {wind_dir})\n"

        growth_rate = result.get("growth_rate_pct")
        if growth_rate is not None and has_rain_or_clouds:
            if growth_rate > 5.0:
                text += f"📈 พัฒนาการเมฆฝน (15 นาทีที่ผ่านมา): กำลังก่อตัวแรงขึ้น (+{growth_rate:.1f}%/15min)\n"
            elif growth_rate < -5.0:
                text += f"📉 พัฒนาการเมฆฝน (15 นาทีที่ผ่านมา): อ่อนกำลังลง ({growth_rate:.1f}%/15min)\n"
            else:
                text += f"➖ พัฒนาการเมฆฝน (15 นาทีที่ผ่านมา): คงที่\n"

    else:
        text = f"ยังไม่มีแนวโน้มฝนตกในบริเวณของคุณภายใน 1-2 ชั่วโมงนี้ (ตรวจสอบด้วย: {endpoint_label})\n"

    return text, actual_endpoint, eta_minutes


async def process_telegram_location(
    chat_id: int,
    lat: float,
    lng: float,
    force_endpoint: str = None,
    message_id_to_edit: int = None,
    show_advanced: bool = False,
    location_name: str = None,
):
    """
    ดึงข้อมูลพยากรณ์ฝนผ่าน WeatherManager (รองรับ fallback chain อัตโนมัติ)
    และส่ง/แก้ไขข้อความผลลัพธ์กลับไปยัง Telegram

    พารามิเตอร์:
      force_endpoint: ถ้าระบุ ("global"/"local") จะบังคับใช้ endpoint นั้นโดยตรง
      message_id_to_edit: ถ้ามี ให้แก้ไขข้อความเดิม (loading state) แทนการส่งใหม่
      location_name: ชื่อของสถานที่ที่จะแสดงในข้อความผลลัพธ์
    """
    try:
        if location_name:
            LAST_ACTIVE_LOCATION[chat_id] = location_name.lower()
        async with get_repo_context() as repo:
            mock_state = await repo.get_mock_state(chat_id)

        weather_manager = WeatherManager()
        result = await weather_manager.predict_rain(
            lat, lng,
            mock_state=mock_state,
            force_endpoint=force_endpoint,
            location_name=location_name,
            chat_id=chat_id,
        )

        text, actual_endpoint, eta_minutes = _build_forecast_text(result)
        
        if location_name:
            text = f"📍 **พื้นที่:** {location_name}\n\n" + text

        if result.get("is_outdated"):
            text = "⚠️ **ยังไม่มีข้อมูลล่าสุดจากกรมอุตุฯ (TMD Radar)**\nแนะนำให้เปลี่ยนไปใช้ API อื่น (เช่น Tomorrow.io หรือ Open-Meteo) แทนชั่วคราวครับ\n"

        # ถ้าทุก API พัง แสดงข้อความ error ชัดเจน แทนการบอกว่า "ไม่มีฝน"
        if actual_endpoint == "error":
            error_text = (
                "⚠️ ขออภัย ไม่สามารถเชื่อมต่อกับระบบพยากรณ์ฝนได้ในขณะนี้\n"
                "กรุณาลองใหม่อีกครั้งในภายหลัง"
            )
            if message_id_to_edit:
                await edit_telegram_message(chat_id, message_id_to_edit, error_text)
            else:
                await send_telegram_message(chat_id, error_text)
            return

        # ตรวจสอบ location ที่บันทึกไว้
        has_existing_loc = False
        async with get_repo_context() as repo:
            existing_loc = await repo.get_location(chat_id)
            if existing_loc:
                has_existing_loc = True

        # Round สำหรับ callback_data
        r_lat = round(lat, 4)
        r_lng = round(lng, 4)

        keyboard = []

        if has_existing_loc:
            text += "\n(คุณมีพิกัดเดิมบันทึกไว้อยู่แล้ว ต้องการบันทึกพิกัดนี้เป็นอะไร หรือลบของเดิมทิ้ง?)"
            keyboard.append([
                {"text": "🏠 บ้าน (2 ด.)", "callback_data": f"loc_save_Home_2m_{r_lat}_{r_lng}"},
                {"text": "🏠 บ้าน (ตป.)", "callback_data": f"loc_save_Home_inf_{r_lat}_{r_lng}"}
            ])
            keyboard.append([
                {"text": "💼 ที่ทำงาน (2 ด.)", "callback_data": f"loc_save_Work_2m_{r_lat}_{r_lng}"},
                {"text": "💼 ที่ทำงาน (ตป.)", "callback_data": f"loc_save_Work_inf_{r_lat}_{r_lng}"}
            ])
            keyboard.append([
                {"text": "📍 ทั่วไป (2 ด.)", "callback_data": f"loc_save_Default_2m_{r_lat}_{r_lng}"},
                {"text": "📍 ทั่วไป (ตป.)", "callback_data": f"loc_save_Default_inf_{r_lat}_{r_lng}"}
            ])
        else:
            text += "(คุณต้องการให้ระบบจดจำตำแหน่งนี้สำหรับการแจ้งเตือนอัตโนมัติไหม?)"
            keyboard.append([
                {"text": "🏠 บ้าน (2 ด.)", "callback_data": f"loc_save_Home_2m_{r_lat}_{r_lng}"},
                {"text": "🏠 บ้าน (ตป.)", "callback_data": f"loc_save_Home_inf_{r_lat}_{r_lng}"}
            ])
            keyboard.append([
                {"text": "💼 ที่ทำงาน (2 ด.)", "callback_data": f"loc_save_Work_2m_{r_lat}_{r_lng}"},
                {"text": "💼 ที่ทำงาน (ตป.)", "callback_data": f"loc_save_Work_inf_{r_lat}_{r_lng}"}
            ])
            keyboard.append([
                {"text": "📍 ทั่วไป (2 ด.)", "callback_data": f"loc_save_Default_2m_{r_lat}_{r_lng}"},
                {"text": "📍 ทั่วไป (ตป.)", "callback_data": f"loc_save_Default_inf_{r_lat}_{r_lng}"}
            ])
            keyboard.append([{"text": "❌ ไม่เป็นไร", "callback_data": "loc_no"}])

        # ปุ่มเปรียบเทียบข้อมูล (Issue #53)
        keyboard.append([{"text": "📊 เปรียบเทียบข้อมูล 4 API", "callback_data": f"compare_api_{r_lat}_{r_lng}"}])

        # ปุ่มควบคุมเป้าเรดาร์แบบแมนนวล (Manual Cloud Targeting)
        if "tmd-radar" in actual_endpoint:
            t_mode = result.get("tracking_mode", "auto")
            if t_mode == "manual":
                locked_lbl = result.get("locked_target_id", "")
                keyboard.append([{"text": f"🔓 ปลดล็อค {locked_lbl} (Auto-track)", "callback_data": f"unlock_target_{r_lat}_{r_lng}"}])
            else:
                approaching_clouds = result.get("approaching_clouds", [])
                all_rain_clusters = result.get("all_rain_clusters", [])
                
                lock_buttons = []
                added_labels = set()
                
                for c in approaching_clouds:
                    lbl = c.get("label")
                    if lbl and lbl != "?" and lbl not in added_labels:
                        lock_buttons.append({"text": f"🔒 ล็อคเป้า {lbl}", "callback_data": f"lock_target_{r_lat}_{r_lng}_{lbl}"})
                        added_labels.add(lbl)
                        
                # Filter ambient clouds (not in approaching_clouds) and sort by distance, taking top 8
                ambient_clouds = [c for c in all_rain_clusters if c.get("label") not in added_labels]
                ambient_clouds.sort(key=lambda c: c.get("dist", 9999))
                
                for c in ambient_clouds[:8]:
                    lbl = c.get("label")
                    if lbl and lbl != "?" and lbl not in added_labels:
                        lock_buttons.append({"text": f"🔒 ล็อคเป้า {lbl}", "callback_data": f"lock_target_{r_lat}_{r_lng}_{lbl}"})
                        added_labels.add(lbl)
                        
                if lock_buttons:
                    # Chunk buttons into rows of 2
                    for i in range(0, len(lock_buttons), 2):
                        keyboard.append(lock_buttons[i:i+2])

        # ปุ่มสลับ Endpoint
        if actual_endpoint in ("rainbow-local", "local", "tmd-radar", "tmd-radar (kkn120)", "tmd-radar (kkn240)", "tmd-radar (skn240)"):
            keyboard.append([{"text": "🔄 สลับไปใช้ Global", "callback_data": f"switch_global_{r_lat}_{r_lng}"}])
        else:
            keyboard.append([{"text": "🔄 สลับไปใช้ Local Radar", "callback_data": f"switch_radar_{r_lat}_{r_lng}"}])

        reply_markup = {"inline_keyboard": keyboard}

        logger.info(f"Preparing to send message to chat_id={chat_id}: '{text[:80]}...'")

        if message_id_to_edit:
            await edit_telegram_message(chat_id, message_id_to_edit, text, reply_markup)
        else:
            await send_telegram_message(chat_id, text, reply_markup)
            
        gif_bytes = result.get("radar_gif_bytes")
        hq_gif_bytes = result.get("radar_hq_gif_bytes")
        static_bytes = result.get("radar_static_bytes")
        tracking_bytes = result.get("radar_tracking_bytes")
        timeline_bytes = result.get("rain_timeline_bytes")
        multiframe_bytes = result.get("radar_multiframe_bytes")
        
        from app.services.telegram import send_telegram_photo, send_telegram_document, send_telegram_raw_document
        
        if show_advanced:
            if static_bytes:
                await send_telegram_photo(chat_id, static_bytes, "radar_latest.png")
                
            if timeline_bytes:
                await send_telegram_photo(chat_id, timeline_bytes, "rain_timeline.png")

            if multiframe_bytes:
                await send_telegram_photo(chat_id, multiframe_bytes, "radar_multiframe.png")
                
            if hq_gif_bytes:
                await send_telegram_raw_document(chat_id, hq_gif_bytes, "radar_nowcast_full.gif")
            
        if tracking_bytes:
            await send_telegram_photo(chat_id, tracking_bytes, "radar_tracking.png")
            
        if gif_bytes:
            await send_telegram_document(chat_id, gif_bytes, "radar_nowcast.gif")

        if show_advanced:
            advanced_data = await weather_manager.get_advanced_alerts(lat, lng, mock_state=mock_state)
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
                
                await send_telegram_message(chat_id, adv_text)
            else:
                await send_telegram_message(chat_id, "ℹ️ ข้อมูลเตือนภัยขั้นสูง: ไม่พบประกาศเตือนภัย พายุ หรือฟ้าผ่าในระยะใกล้")

    except Exception as e:
        logger.error(f"Error processing telegram location: {e}")
        error_text = "ขออภัย ไม่สามารถดึงข้อมูลพยากรณ์ฝนได้ในขณะนี้"
        try:
            if message_id_to_edit:
                await edit_telegram_message(chat_id, message_id_to_edit, error_text)
            else:
                await send_telegram_message(chat_id, error_text)
        except Exception as inner_e:
            logger.error(f"Failed to send fallback error message: {inner_e}")


async def handle_callback_query(callback_query: dict):
    query_id = callback_query.get("id")
    from_user = callback_query.get("from", {})
    chat_id = from_user.get("id")
    data = callback_query.get("data", "")
    message = callback_query.get("message", {})
    message_id = message.get("message_id")

    if not chat_id or not query_id:
        return

    answer_text = ""
    async with get_repo_context() as repo:
        if data.startswith("loc_save_"):
            parts = data.split("_")
            # Format: loc_save_<name>_<retention>_<lat>_<lng>
            # Example: loc_save_Home_2m_13.1_100.1
            if len(parts) >= 6:
                try:
                    name = parts[2].lower()  # e.g. "home", "work", "default"
                    retention_str = parts[3]
                    lat = float(parts[4])
                    lng = float(parts[5])
                    retention = "TWO_MONTHS" if retention_str == "2m" else "FOREVER"
                    await repo.save_location(chat_id, lat, lng, retention, name)
                    answer_text = f"บันทึกข้อมูลพิกัด {name} เรียบร้อยแล้ว"
                except ValueError:
                    answer_text = "เกิดข้อผิดพลาดในการบันทึกพิกัด"
        elif data.startswith("loc_del_"):
            parts = data.split("_")
            if len(parts) >= 3:
                name = parts[2].lower()
                await repo.delete_location(chat_id, name)
                answer_text = f"ลบข้อมูลพิกัด {name} เรียบร้อยแล้ว"
        elif data == "loc_no":
            answer_text = "ระบบรับทราบ จะไม่จดจำตำแหน่งใหม่"
        elif data.startswith("fb_falsealarm_"):
            parts = data.split("_")
            if len(parts) >= 4:
                try:
                    lat = float(parts[2])
                    lng = float(parts[3])
                    
                    context_msg = "User reported false alarm from inline button"
                    if len(parts) >= 6:
                        ep_map_rev = {"t": "Tomorrow.io", "rl": "Rainbow Local", "rg": "Rainbow Global", "xw": "Xweather", "om": "Open-Meteo", "u": "Unknown"}
                        ep_name = ep_map_rev.get(parts[4], parts[4])
                        max_r = parts[5]
                        context_msg = f"Source: {ep_name}, max_rain: {max_r} mm/hr"
                        
                    await repo.save_feedback(chat_id, lat, lng, "false_alarm", context_msg)
                    answer_text = "ขอบคุณสำหรับข้อมูล เราจะนำไปปรับปรุงความแม่นยำครับ"
                except Exception as e:
                    logger.error(f"Error parsing false alarm data: {e}")
                    answer_text = "เกิดข้อผิดพลาดในการบันทึกข้อมูล"

    # Handle Developer Raw Data Request
    if data.startswith("raw_"):
        if not await check_admin_access(chat_id):
            answer_text = "คุณไม่มีสิทธิ์เข้าถึงข้อมูลดิบ"
        else:
            parts = data.split("_")
            if len(parts) >= 3:
                try:
                    lat = float(parts[1])
                    lng = float(parts[2])

                    # ดึงข้อมูลผ่าน WeatherManager (รองรับ fallback chain)
                    weather_manager = WeatherManager()
                    result = await weather_manager.predict_rain(lat, lng, chat_id=chat_id)

                    logger.info(f"Raw API Data for {lat}, {lng}: {json.dumps(result)}")

                    raw_bytes = json.dumps(result, indent=2).encode("utf-8")
                    await send_telegram_document(chat_id, raw_bytes, f"raw_{lat}_{lng}.json")
                    answer_text = "ส่งไฟล์ข้อมูลดิบเรียบร้อยแล้ว"
                except Exception as e:
                    logger.error(f"Error fetching raw data: {e}")
                    answer_text = "เกิดข้อผิดพลาดในการดึงข้อมูลดิบ"
            else:
                answer_text = "รูปแบบข้อมูลดิบไม่ถูกต้อง"

    # Handle Manual target lock callbacks
    if data.startswith("lock_target_"):
        parts = data.split("_")
        if len(parts) >= 5:
            try:
                lat = float(parts[2])
                lng = float(parts[3])
                label = parts[4]
                
                answer_text = f"กำลังล็อคเป้ากลุ่มฝน [{label}]..."
                
                weather_manager = WeatherManager()
                res = await weather_manager.predict_rain(lat, lng, chat_id=chat_id)
                clouds = res.get("approaching_clouds", [])
                all_clusters = res.get("all_rain_clusters", [])
                
                target_c = None
                for c in clouds:
                    if c.get("label") == label:
                        target_c = c
                        break
                if not target_c:
                    for c in all_clusters:
                        if c.get("label") == label:
                            target_c = c
                            break
                
                if target_c:
                    cx = target_c["cx"]
                    cy = target_c["cy"]
                    async with get_repo_context() as repo:
                        # Resolve which named location row corresponds to the
                        # locked coordinate, so tracking persists against the
                        # right place rather than blindly hitting "default".
                        # If no saved row matches this coordinate, upsert the
                        # "default" row to the locked coordinate.
                        all_locs = await repo.get_user_locations(chat_id)
                        chosen_name = "default"
                        for l in all_locs:
                            if (abs(l.latitude - lat) < 1e-6
                                    and abs(l.longitude - lng) < 1e-6):
                                chosen_name = l.name
                                break
                        else:
                            await repo.save_location(
                                chat_id, lat, lng, "FOREVER", name="default"
                            )
                        await repo.update_tracking_mode(
                            chat_id=chat_id,
                            tracking_mode="manual",
                            locked_target_id=label,
                            locked_target_cx=cx,
                            locked_target_cy=cy,
                            name=chosen_name,
                        )
                    await process_telegram_location(
                        chat_id, lat, lng,
                        message_id_to_edit=message_id,
                        location_name=chosen_name,
                    )
                else:
                    answer_text = f"ไม่พบกลุ่มฝน [{label}] หรือเมฆสลายตัวไปแล้ว"
            except Exception as e:
                logger.error(f"Error handling lock target callback: {e}")
                answer_text = "เกิดข้อผิดพลาดในการล็อคเป้า"

    elif data.startswith("unlock_target_"):
        parts = data.split("_")
        if len(parts) >= 4:
            try:
                lat = float(parts[2])
                lng = float(parts[3])
                
                answer_text = "กำลังปลดล็อคกลุ่มฝน..."
                
                async with get_repo_context() as repo:
                    await repo.update_tracking_mode(
                        chat_id=chat_id,
                        tracking_mode="auto",
                    )
                await process_telegram_location(
                    chat_id, lat, lng,
                    message_id_to_edit=message_id,
                )
            except Exception as e:
                logger.error(f"Error handling unlock target callback: {e}")
                answer_text = "เกิดข้อผิดพลาดในการปลดล็อคเป้า"

    # Handle Endpoint Switch (พร้อม Loading State)
    if data.startswith("switch_radar_") or data.startswith("switch_global_"):
        parts = data.split("_")
        if len(parts) >= 4:
            try:
                lat = float(parts[2])
                lng = float(parts[3])
                force_endpoint = "local" if data.startswith("switch_radar_") else "global"

                answer_text = "กำลังดึงข้อมูลใหม่..."
                await process_telegram_location(
                    chat_id, lat, lng,
                    force_endpoint=force_endpoint,
                    message_id_to_edit=message_id,
                )
            except Exception as e:
                logger.error(f"Error handling switch endpoint: {e}")
                answer_text = "เกิดข้อผิดพลาดในการสลับแหล่งข้อมูล"

    # Handle Force API
    elif data.startswith("force_api_"):
        parts = data.split("_")
        if len(parts) >= 5:
            provider = parts[2]
            try:
                lat = float(parts[3])
                lng = float(parts[4])
                
                loading_msg_id = await send_telegram_message_return_id(chat_id, f"⏳ กำลังประมวลผลสภาพอากาศด้วย {provider}...")
                await process_telegram_location(chat_id, lat, lng, force_endpoint=provider, message_id_to_edit=loading_msg_id)
                await answer_callback_query(query_id)
            except ValueError:
                logger.error("Invalid lat/lng in force_api")

    # Handle View Insights (Issue #42)
    if data.startswith("compare_api_"):
        parts = data.split("_")
        if len(parts) >= 4:
            try:
                lat = float(parts[2])
                lng = float(parts[3])
                
                answer_text = "กำลังดึงข้อมูลเปรียบเทียบ..."
                
                async with get_repo_context() as repo:
                    mock_state = await repo.get_mock_state(chat_id)
                
                weather_manager = WeatherManager()
                results = await weather_manager.compare_all_apis(lat, lng, mock_state=mock_state)
                
                # Format results
                from datetime import datetime, timezone, timedelta
                bkk_tz = timezone(timedelta(hours=7))
                update_time_str = datetime.now(bkk_tz).strftime("%d/%m/%Y %H:%M:%S")
                text = f"📊 ข้อมูลเปรียบเทียบ 4 API (พิกัด {lat}, {lng}):\n"
                text += f"🔄 ข้อมูลอัปเดตล่าสุด: {update_time_str}\n\n"
                
                display_names = {
                    "xweather": "Xweather (Premium)",
                    "tomorrow": "Tomorrow.io",
                    "rainbow-local": "Rainbow Local",
                    "rainbow-global": "Rainbow Global"
                }
                for k, v in results.items():
                    disp_k = display_names.get(k, k)
                    accuracy = v.get("accuracy_score", 0.0)
                    acc_percent = accuracy * 100.0
                    
                    if "error" in v:
                        text += f"🔹 {disp_k} (ความแม่นยำ: {acc_percent:.1f}%):\n  ❌ ข้อผิดพลาด: {v['error']}\n\n"
                    else:
                        max_rain = v.get('max_rain', 0)
                        text += f"🔹 {disp_k} (ความแม่นยำ: {acc_percent:.1f}%):\n"
                        
                        rain_summary = v.get("rain_summary")
                        if rain_summary:
                            # Replace newlines with indent
                            indented_summary = rain_summary.replace("\n", "\n  ")
                            text += f"  {indented_summary}\n"
                            
                            wind_kmh = v.get("wind_speed_kmh", 0)
                            wind_dir = v.get("wind_dir_text", "ไม่ทราบ")
                            if wind_kmh > 0:
                                if "tmd-radar" in disp_k.lower() or "tmd-radar" in k.lower():
                                    if "ไม่พบฝน" not in rain_summary:
                                        text += f"  🌬️ ทิศที่พายุเคลื่อนที่ไป: {wind_kmh} km/h (ทิศ {wind_dir})\n"
                                else:
                                    text += f"  🌬️ ลม: {wind_kmh} km/h (ทิศ {wind_dir})\n"
                            text += "\n"
                        else:
                            text += f"  💧 ปริมาณฝนสูงสุด: {max_rain:.2f} mm/hr\n"
                            text += f"  🌧️ ความรุนแรง: {v.get('intensity', 'ไม่ทราบ')}\n"
                            
                            wind_kmh = v.get("wind_speed_kmh", 0)
                            wind_dir = v.get("wind_dir_text", "ไม่ทราบ")
                            if wind_kmh > 0:
                                if "tmd-radar" in disp_k.lower() or "tmd-radar" in k.lower():
                                    if "ไม่พบฝน" not in v.get("rain_summary", ""):
                                        text += f"  🌬️ ทิศที่พายุเคลื่อนที่ไป: {wind_kmh} km/h (ทิศ {wind_dir})\n"
                                else:
                                    text += f"  🌬️ ลม: {wind_kmh} km/h (ทิศ {wind_dir})\n"
                                
                            storm_distance = v.get("storm_distance_km")
                            if storm_distance is not None:
                                text += f"  🌪️ ระยะห่างพายุ: {storm_distance} กม.\n"
                            
                            if max_rain > 0:
                                # Calculate ETA
                                eta_minutes = None
                                predictions = v.get("predictions", [])
                                if predictions:
                                    try:
                                        base_time = datetime.fromisoformat(predictions[0].get("time", "").replace("Z", "+00:00"))
                                        for pred in predictions:
                                            if pred.get("rain", 0) > 0:
                                                pred_time = datetime.fromisoformat(pred.get("time", "").replace("Z", "+00:00"))
                                                eta_minutes = int((pred_time - base_time).total_seconds() / 60)
                                                break
                                    except Exception:
                                        pass
                                        
                                duration = v.get("duration_minutes", 0)
                                
                                if eta_minutes is not None:
                                    start_dt = datetime.now(bkk_tz) + timedelta(minutes=eta_minutes)
                                    end_dt = start_dt + timedelta(minutes=duration)
                                    start_str = start_dt.strftime("%H:%M")
                                    end_str = end_dt.strftime("%H:%M")
                                    
                                    if eta_minutes == 0:
                                        text += f"  ⏱️ เริ่มตก: ขณะนี้ ({start_str} น.)\n"
                                    else:
                                        text += f"  ⏱️ เริ่มตกในอีก: {format_duration_text(eta_minutes)} ({start_str} น.)\n"
                                        
                                    if duration > 0:
                                        text += f"  ⏳ ตกต่อเนื่อง: {format_duration_text(duration)} (จนถึง {end_str} น.)\n"
                                    
                            text += "\n"
                
                keyboard = []
                row = []
                for ep in results.keys():
                    row.append({"text": f"✅ {display_names.get(ep, ep)}", "callback_data": f"force_api_{ep}_{lat}_{lng}"})
                    if len(row) == 2:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)
                reply_markup = {"inline_keyboard": keyboard}
                
                await edit_telegram_message(chat_id, message_id, text, reply_markup=reply_markup)
                
                await answer_callback_query(query_id)
                
            except Exception as e:
                logger.error(f"Error handling compare_api: {e}")
                answer_text = "เกิดข้อผิดพลาดในการดึงข้อมูลเปรียบเทียบ"

    await answer_callback_query(query_id, text=answer_text)
    
    async with httpx.AsyncClient() as client:
        # ลบ Inline Keyboard (เฉพาะ action ที่เกี่ยวกับ location ไม่ใช่ raw/switch)
        if message_id and not (data.startswith("raw_") or data.startswith("switch_")):
            await client.post(TELEGRAM_EDIT_REPLY_MARKUP_URL, json={
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_markup": {"inline_keyboard": []}
            })


async def handle_lock_command(chat_id: int, command: str):
    import re
    cx, cy = None, None
    grid_lbl = None
    grid_col_idx = None
    grid_row_idx = None
    
    try:
        async with get_repo_context() as repo:
            locs = await repo.get_user_locations(chat_id)
            if not locs:
                await send_telegram_message(chat_id, "⚠️ ไม่พบข้อมูลพิกัดหลักของคุณ กรุณาส่งพิกัดก่อนใช้งานคำสั่งนี้")
                return
            
            raw_args = command.removeprefix("/lock").strip()
            args = raw_args.split()
            if not args:
                await send_telegram_message(
                    chat_id, 
                    "⚠️ รูปแบบคำสั่งไม่ถูกต้อง\n"
                    "กรุณาใช้:\n"
                    "- ล็อคช่องตาราง: `/lock [ชื่อพิกัด] D2` หรือ `/lock D2`\n"
                    "- ล็อคพิกัดจริง: `/lock [ชื่อพิกัด] 13.75 100.5` หรือ `/lock 13.75 100.5`"
                )
                return
                
            first_arg = args[0].lower()
            matched_loc = None
            for l in locs:
                if l.name.lower() == first_arg:
                    matched_loc = l
                    break
                    
            if matched_loc:
                loc = matched_loc
                target_str = " ".join(args[1:])
            else:
                loc = None
                active_loc_name = LAST_ACTIVE_LOCATION.get(chat_id)
                if active_loc_name:
                    for l in locs:
                        if l.name.lower() == active_loc_name.lower():
                            loc = l
                            break
                # Prefer the most recently pinned Telegram location when no
                # saved-location name was named or matched. Upsert the pinned
                # coordinate into the "default" row so tracking can persist and
                # the re-forecast after locking uses the same coordinate.
                if not loc:
                    pinned = LAST_PINNED_LOCATION.get(chat_id)
                    if pinned:
                        pinned_lat, pinned_lng = pinned
                        loc = await repo.save_location(
                            chat_id, pinned_lat, pinned_lng, "FOREVER", name="default"
                        )
                if not loc:
                    for name_to_find in ["home", "default", "work"]:
                        for l in locs:
                            if l.name.lower() == name_to_find:
                                loc = l
                                break
                        if loc:
                            break
                if not loc:
                    loc = locs[0]
                target_str = raw_args
                
            lat, lng = loc.latitude, loc.longitude
            loc_name = loc.name
            prev_cx = loc.locked_target_cx
            prev_cy = loc.locked_target_cy
        
        grid_match = re.match(r"^([a-hA-H])[-_]?([1-8])$", target_str.strip())
        cloud_label_match = re.match(r"^[a-zA-Z]{1,2}$", target_str.strip())
        
        is_grid_lock = False
        is_label_lock = False
        
        if grid_match:
            is_grid_lock = True
            col_char = grid_match.group(1).upper()
            row_char = grid_match.group(2)
            grid_col_idx = ord(col_char) - ord('A')
            grid_row_idx = int(row_char) - 1
            cx = int((grid_col_idx + 0.5) * 100)
            cy = int((grid_row_idx + 0.5) * 100)
            grid_lbl = f"{col_char}{row_char}"
        elif cloud_label_match:
            is_label_lock = True
            grid_lbl = target_str.strip().upper()
        else:
            parts = re.findall(r"[-+]?\d*\.\d+|\d+", target_str)
            if len(parts) < 2:
                await send_telegram_message(
                    chat_id, 
                    "⚠️ รูปแบบตัวชี้เป้าไม่ถูกต้อง\n"
                    "กรุณาใช้:\n"
                    "- ล็อคกลุ่มฝน: `/lock [ชื่อพิกัด] A` หรือ `/lock A`\n"
                    "- ล็อคช่องตาราง: `/lock [ชื่อพิกัด] D4`\n"
                    "- ล็อคพิกัดจริง: `/lock [ชื่อพิกัด] 13.75 100.5`"
                )
                return
            
            val1 = float(parts[0])
            val2 = float(parts[1])
            is_latlng = (5.0 <= val1 <= 25.0) and (95.0 <= val2 <= 107.0)
            
            if is_latlng:
                cx, cy = None, None
            else:
                cx, cy = int(val1), int(val2)
                
        import math
        from app.services.weather_manager import WeatherManager
        from app.services.tmd_radar_processor import TMDRadarProcessor
        from app.services.tmd_radar_config import STATIONS

        def station_distance(station_code: str) -> float:
            conf = STATIONS[station_code]
            return math.hypot(lat - conf.center_lat, lng - conf.center_lng)

        processor = None
        station_code = None
        for candidate in sorted(["kkn120", "kkn240", "skn240"], key=station_distance):
            candidate_processor = TMDRadarProcessor(candidate)
            user_px, user_py = candidate_processor.latlng_to_pixel(lat, lng, is_loop=False)
            if user_px is not None and user_py is not None:
                processor = candidate_processor
                station_code = candidate
                break

        if processor is None or station_code is None:
            await send_telegram_message(chat_id, "⚠️ พิกัดหลักอยู่นอกขอบเขตของแผนที่เรดาร์")
            return

        if not grid_lbl and "parts" in locals() and len(parts) >= 2:
            val1 = float(parts[0])
            val2 = float(parts[1])
            is_latlng = (5.0 <= val1 <= 25.0) and (95.0 <= val2 <= 107.0)
            if is_latlng:
                cx, cy = processor.latlng_to_pixel(val1, val2, is_loop=False)

        wm = WeatherManager()
        
        cache_data = await wm.load_persistent_cache_to_memory(station_code, processor)
        
        has_cloud = False
        max_dbz = 0.0
        peak_x, peak_y = cx, cy
        vx, vy = 0.0, 0.0
        frame_w = processor.config.static_crop_width
        frame_h = processor.config.static_crop_height
        
        if cache_data:
            frames, _, _, flow, _, _, _ = cache_data
            latest_frame = frames[-1]
            h, w = latest_frame.shape[:2]
            frame_w, frame_h = w, h
            
            if is_grid_lock:
                user_px, user_py = processor.latlng_to_pixel(lat, lng, is_loop=False)
                crop_r = 120
                crop_x1 = max(0, user_px - crop_r)
                crop_y1 = max(0, user_py - crop_r)
                crop_x2 = min(w, user_px + crop_r)
                crop_y2 = min(h, user_py + crop_r)
                cell_w = (crop_x2 - crop_x1) / 8.0
                cell_h = (crop_y2 - crop_y1) / 8.0
                x_min = max(0, int(crop_x1 + grid_col_idx * cell_w))
                x_max = min(w, int(crop_x1 + (grid_col_idx + 1) * cell_w))
                y_min = max(0, int(crop_y1 + grid_row_idx * cell_h))
                y_max = min(h, int(crop_y1 + (grid_row_idx + 1) * cell_h))
                cx = int((x_min + x_max) / 2)
                cy = int((y_min + y_max) / 2)
                peak_x, peak_y = cx, cy
                
                for y_p in range(y_min, y_max):
                    for x_p in range(x_min, x_max):
                        dbz = processor.get_dbz_at_pixel(latest_frame, x_p, y_p)
                        if dbz >= 10.0:
                            has_cloud = True
                            if dbz > max_dbz:
                                max_dbz = dbz
                                peak_x, peak_y = x_p, y_p
                                
                if has_cloud:
                    cx, cy = peak_x, peak_y
                    vx = float(flow[peak_y, peak_x, 0])
                    vy = float(flow[peak_y, peak_x, 1])
            elif is_label_lock:
                res = await wm.predict_rain(lat, lng, chat_id=chat_id)
                clouds = res.get("approaching_clouds", [])
                all_clusters = res.get("all_rain_clusters", [])
                
                target_c = None
                for c in clouds:
                    if c.get("label", "").upper() == grid_lbl:
                        target_c = c
                        break
                if not target_c:
                    for c in all_clusters:
                        if c.get("label", "").upper() == grid_lbl:
                            target_c = c
                            break
                            
                if target_c:
                    cx = target_c["cx"]
                    cy = target_c["cy"]
                    has_cloud = True
                    max_dbz = target_c.get("dbz_now", 0.0)
                    peak_x, peak_y = cx, cy
                    vx = float(flow[cy, cx, 0])
                    vy = float(flow[cy, cx, 1])
                else:
                    await send_telegram_message(
                        chat_id,
                        f"⚠️ ไม่พบกลุ่มฝนป้ายกำกับ [{grid_lbl}] ในบริเวณรอบตัวคุณ หรือเมฆสลายตัวไปแล้ว"
                    )
                    return
            else:
                search_radius = 25
                x_min = max(0, cx - search_radius)
                x_max = min(w, cx + search_radius)
                y_min = max(0, cy - search_radius)
                y_max = min(h, cy + search_radius)
                
                for y_p in range(y_min, y_max):
                    for x_p in range(x_min, x_max):
                        dbz = processor.get_dbz_at_pixel(latest_frame, x_p, y_p)
                        if dbz >= 10.0:
                            has_cloud = True
                            if dbz > max_dbz:
                                max_dbz = dbz
                                peak_x, peak_y = x_p, y_p
                                
                if has_cloud:
                    cx, cy = peak_x, peak_y
                    vx = float(flow[peak_y, peak_x, 0])
                    vy = float(flow[peak_y, peak_x, 1])
        elif is_grid_lock:
            user_px, user_py = processor.latlng_to_pixel(lat, lng, is_loop=False)
            crop_r = 120
            crop_x1 = max(0, user_px - crop_r)
            crop_y1 = max(0, user_py - crop_r)
            crop_x2 = min(frame_w, user_px + crop_r)
            crop_y2 = min(frame_h, user_py + crop_r)
            cell_w = (crop_x2 - crop_x1) / 8.0
            cell_h = (crop_y2 - crop_y1) / 8.0
            cx = int(crop_x1 + (grid_col_idx + 0.5) * cell_w)
            cy = int(crop_y1 + (grid_row_idx + 0.5) * cell_h)
            peak_x, peak_y = cx, cy

        if cx is None or cy is None or not (0 <= cx < frame_w and 0 <= cy < frame_h):
            await send_telegram_message(chat_id, "⚠️ พิกัดอยู่นอกขอบเขตของแผนที่เรดาร์")
            return

        eta_text = ""
        comparison_text = ""
        wind_speed = 0.0
        wind_dir = "ไม่ทราบ"
        
        if has_cloud:
            user_px, user_py = processor.latlng_to_pixel(lat, lng)
            dx = user_px - peak_x
            dy = user_py - peak_y
            dist = math.sqrt(dx*dx + dy*dy)
            
            wind_speed = processor.get_wind_speed_kmh_from_vector(vx, vy)
            wind_dir = processor.get_wind_direction_text_from_vector(vx, vy)
            
            if dist > 0:
                v_close = (vx * dx + vy * dy) / dist
            else:
                v_close = 0
                
            if v_close > 0.05:
                t_mins = int((dist / v_close) * 15)
                if t_mins >= 60:
                    hrs = t_mins // 60
                    mins = t_mins % 60
                    eta_text = f"⏱️ คาดว่าจะเคลื่อนเข้าหาคุณในอีกประมาณ: {hrs} ชม. {mins} นาที\n"
                else:
                    eta_text = f"⏱️ คาดว่าจะเคลื่อนเข้าหาคุณในอีกประมาณ: {t_mins} นาที\n"
            else:
                eta_text = f"💨 ทิศทางลมปัจจุบัน: {wind_speed:.1f} กม./ชม. (ทิศ {wind_dir}) — แนวโน้มเคลื่อนที่ขนานหรือออกห่างจากตำแหน่งคุณ\n"
                
            if prev_cx is not None and prev_cy is not None:
                prev_dist = math.sqrt((user_px - prev_cx)**2 + (user_py - prev_cy)**2)
                lon_diff = processor.config.bbox.lng_max - processor.config.bbox.lng_min
                width_km = lon_diff * 111.0
                km_per_pixel = width_km / 800.0
                
                delta_km = (prev_dist - dist) * km_per_pixel
                if delta_km > 0.1:
                    comparison_text = f"📈 เมื่อเทียบกับรอบก่อนหน้า: กลุ่มฝนขยับเข้าใกล้คุณมากขึ้น {delta_km:.1f} กม. (เร็วขึ้น/กระชั้นชิดขึ้น)\n"
                elif delta_km < -0.1:
                    comparison_text = f"📉 เมื่อเทียบกับรอบก่อนหน้า: กลุ่มฝนขยับห่างออกไป {abs(delta_km):.1f} กม.\n"
                else:
                    comparison_text = f"📊 เมื่อเทียบกับรอบก่อนหน้า: อยู่ห่างที่ระยะใกล้เคียงเดิม\n"

        async with get_repo_context() as repo:
            await repo.update_tracking_mode(
                chat_id=chat_id,
                tracking_mode="manual",
                locked_target_id=grid_lbl or "MANUAL",
                locked_target_cx=cx,
                locked_target_cy=cy,
                name=loc_name
            )
            
        if not has_cloud:
            success_msg = f"⚠️ สังเกตการณ์: ไม่พบกลุ่มเมฆฝนในช่องตาราง {grid_lbl or target_str} (ความแรงฝน < 10 dBZ)\n"
            success_msg += f"ตำแหน่งเป้าหมาย: {loc_name.capitalize()}\n"
            success_msg += "ระบบได้บันทึกพิกัดเป้าเล็งไว้แล้ว (คุณสามารถเช็คภาพเรดาร์ล่าสุดเพื่อยืนยัน)"
        else:
            success_msg = f"🔒 ตั้งค่าล็อคเป้าแมนนวลสำเร็จ!\n"
            if is_label_lock:
                success_msg += f"กลุ่มฝน: [{grid_lbl}] (Pixel: {cx}, {cy})\n"
            elif grid_lbl:
                success_msg += f"ช่องตาราง: {grid_lbl} (Pixel: {cx}, {cy})\n"
            else:
                success_msg += f"พิกัดเรดาร์: Pixel ({cx}, {cy})\n"
            success_msg += f"ตำแหน่งเป้าหมาย: {loc_name.capitalize()}\n\n"
            success_msg += f"🔍 ข้อมูลกลุ่มฝนในพื้นที่ล็อคเป้า:\n"
            success_msg += f"  💧 ความแรงฝนสูงสุด: {max_dbz:.1f} dBZ\n"
            success_msg += f"  🌬️ ลมเคลื่อนที่: {wind_speed:.1f} กม./ชม. (ทิศ {wind_dir})\n"
            if eta_text:
                success_msg += f"  {eta_text}"
            if comparison_text:
                success_msg += f"  {comparison_text}"
            success_msg += "\nระบบจะใช้ข้อมูลนี้ในการพยากรณ์รอบถัดไป"
        
        await send_telegram_message(chat_id, success_msg)
        await process_telegram_location(chat_id, lat, lng, location_name=loc_name)
    except Exception as e:
        logger.error(f"Error handling lock command: {e}")
        await send_telegram_message(chat_id, f"❌ เกิดข้อผิดพลาด: {str(e)}")


async def handle_unlock_command(chat_id: int, command: str):
    try:
        async with get_repo_context() as repo:
            locs = await repo.get_user_locations(chat_id)
            if not locs:
                await send_telegram_message(chat_id, "⚠️ ไม่พบข้อมูลพิกัดหลักของคุณ")
                return
                
            arg = command.removeprefix("/unlock").strip().lower()
            loc = None
            if arg:
                for l in locs:
                    if l.name.lower() == arg:
                        loc = l
                        break
                        
            if not loc:
                active_loc_name = LAST_ACTIVE_LOCATION.get(chat_id)
                if active_loc_name:
                    for l in locs:
                        if l.name.lower() == active_loc_name.lower():
                            loc = l
                            break
                if not loc:
                    for name_to_find in ["home", "default", "work"]:
                        for l in locs:
                            if l.name.lower() == name_to_find:
                                loc = l
                                break
                        if loc:
                            break
                if not loc:
                    loc = locs[0]
                    
            await repo.update_tracking_mode(
                chat_id=chat_id,
                tracking_mode="auto",
                name=loc.name
            )
            lat, lng = loc.latitude, loc.longitude
            loc_name = loc.name
            
        await send_telegram_message(chat_id, f"🔓 ปลดล็อคกลุ่มฝน (Auto-track) ของ {loc_name.capitalize()} เรียบร้อยแล้ว")
        await process_telegram_location(chat_id, lat, lng, location_name=loc_name)
    except Exception as e:
        logger.error(f"Error handling unlock command: {e}")
        await send_telegram_message(chat_id, f"❌ เกิดข้อผิดพลาด: {str(e)}")


async def handle_mylocation_command(chat_id: int):
    async with get_repo_context() as repo:
        locs = await repo.get_user_locations(chat_id)

    if not locs:
        text = "คุณยังไม่ได้บันทึกตำแหน่งใดๆ ไว้ในระบบ"
        reply_markup = None
    else:
        text = "📍 พิกัดที่บันทึกไว้ของคุณ:\n\n"
        keyboard = []
        for loc in locs:
            expires = "จำตลอดไป"
            if loc.expires_at:
                expires = loc.expires_at.strftime("%Y-%m-%d %H:%M:%S UTC")

            loc_name = loc.name if loc.name else "default"

            icon = "📍"
            if loc_name.lower() == "home":
                icon = "🏠"
            elif loc_name.lower() == "work":
                icon = "💼"

            text += f"{icon} {loc_name.capitalize()}: {loc.latitude}, {loc.longitude}\n"
            text += f"⏳ วันหมดอายุ: {expires}\n\n"

            keyboard.append([{"text": f"🗑️ ลบ {loc_name.capitalize()}", "callback_data": f"loc_del_{loc_name.lower()}"}])

        text += "หากต้องการเปลี่ยนแปลงพิกัด ให้ส่ง Location ใหม่อีกครั้ง หรือกดปุ่มด้านล่างเพื่อลบข้อมูล"

        reply_markup = {
            "inline_keyboard": keyboard
        }

    await send_telegram_message(chat_id, text, reply_markup)


async def handle_radar_command(chat_id: int):
    async with get_repo_context() as repo:
        loc = await repo.get_location(chat_id)

    if not loc:
        text = "คุณยังไม่ได้บันทึกตำแหน่งใดๆ ไว้ในระบบ กรุณาส่งพิกัด Location ของคุณให้บอทก่อนครับ 📍"
        await send_telegram_message(chat_id, text)
    else:
        text = "📡 คุณสามารถเช็คเรดาร์ฝนด้วยตัวเองได้จากแหล่งข้อมูลเหล่านี้:"
        is_dev = str(chat_id) in DEVELOPER_CHAT_IDS
        reply_markup = get_radar_inline_keyboard(loc.latitude, loc.longitude, is_developer=is_dev)
        await send_telegram_message(chat_id, text, reply_markup=reply_markup)


async def handle_metrics_command(chat_id: int, command: str, username: str = ""):
    if not await check_admin_access(chat_id):
        return

    if str(chat_id) not in DEVELOPER_CHAT_IDS:
        log_audit_event("admin_command_executed", chat_id, username, {"command": command})

    parts = command.strip().split()
    days = 7
    if len(parts) > 1:
        try:
            days = int(parts[1])
        except ValueError:
            pass

    async with get_repo_context() as repo:
        try:
            logs = await repo.get_cron_metrics(days=days)
        except Exception as e:
            logger.error(f"Failed to fetch metrics: {e}")
            await send_telegram_message(chat_id, "❌ ไม่สามารถดึงข้อมูล metrics ได้ในขณะนี้")
            return

    if not logs:
        await send_telegram_message(chat_id, f"ℹ️ ไม่มีข้อมูล metrics ในช่วง {days} วันที่ผ่านมา")
        return

    import io
    import csv
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["routine_name", "run_at", "duration_s", "alerts_sent", "locations_checked", "errors", "extra_data"])
    
    for log in logs:
        run_at_str = log.get("run_at").isoformat() if log.get("run_at") else ""
        extra_str = json.dumps(log.get("extra_data"), ensure_ascii=False) if log.get("extra_data") else ""
        writer.writerow([
            log.get("routine_name"),
            run_at_str,
            log.get("duration_s"),
            log.get("alerts_sent"),
            log.get("locations_checked"),
            log.get("errors"),
            extra_str
        ])
        
    csv_data = output.getvalue().encode("utf-8")
    
    await send_telegram_document(chat_id, csv_data, f"metrics_{days}_days.csv")


async def handle_setbudget_command(chat_id: int, command: str, username: str = ""):
    if not await check_admin_access(chat_id):
        return

    if str(chat_id) not in DEVELOPER_CHAT_IDS:
        log_audit_event("admin_command_executed", chat_id, username, {"command": command})

    parts = command.strip().split()
    if len(parts) < 2:
        await send_telegram_message(
            chat_id, "❌ รูปแบบการใช้งานไม่ถูกต้อง กรุณาพิมพ์: /setbudget <จำนวนงบประมาณ (ตัวเลข)>"
        )
        return

    try:
        amount = float(parts[1])
    except ValueError:
        await send_telegram_message(
            chat_id, "❌ รูปแบบการใช้งานไม่ถูกต้อง กรุณาพิมพ์: /setbudget <จำนวนงบประมาณ (ตัวเลข)>"
        )
        return

    from app.services.billing_service import BillingService
    billing_svc = BillingService()
    success = await billing_svc.update_budget(amount)
    
    if success:
        await send_telegram_message(
            chat_id, f"✅ ปรับงบประมาณ GCP สำเร็จเป็น {amount} THB เรียบร้อยแล้ว"
        )
    else:
        await send_telegram_message(
            chat_id, "❌ ไม่สามารถปรับงบประมาณ GCP ได้ กรุณาตรวจสอบ logs ของระบบ"
        )


async def handle_tmd_fallback_command(chat_id: int, command: str, username: str = ""):
    """
    /tmd_fallback on
    /tmd_fallback off
    """
    if not await check_admin_access(chat_id):
        return

    if str(chat_id) not in DEVELOPER_CHAT_IDS:
        log_audit_event("admin_command_executed", chat_id, username, {"command": command})

    parts = command.strip().split()
    if len(parts) < 2:
        async with get_repo_context() as repo:
            sys_settings = await repo.get_system_settings()
            current_status = sys_settings.get("enable_gif_fallback", True)
            
        status_str = "ON 🟢" if current_status else "OFF 🔴"
        await send_telegram_message(
            chat_id,
            f"ℹ️ สถานะ GIF Fallback ปัจจุบัน: {status_str}\n"
            "พิมพ์ `/tmd_fallback on` หรือ `/tmd_fallback off` เพื่อเปลี่ยน"
        )
        return

    action = parts[1].lower()
    enable = True if action == "on" else False

    async with get_repo_context() as repo:
        sys_settings = await repo.get_system_settings()
        sys_settings["enable_gif_fallback"] = enable
        await repo.set_system_settings(sys_settings)

    status_str = "ON 🟢" if enable else "OFF 🔴"
    await send_telegram_message(
        chat_id,
        f"✅ ตั้งค่า GIF Fallback เป็น {status_str} เรียบร้อยแล้ว"
    )


async def handle_devmock_command(chat_id: int, command: str, username: str = ""):
    if not await check_admin_access(chat_id):
        return

    if str(chat_id) not in DEVELOPER_CHAT_IDS:
        log_audit_event("admin_command_executed", chat_id, username, {"command": command})

    async with get_repo_context() as repo:
        if command == "/devmock rain":
            await repo.set_mock_state(chat_id, "rain")

            # Reset cooldown สำหรับทุก location ของ user นี้ เพื่อให้ alert ยิงทันที
            locs = await repo.get_user_locations(chat_id)
            for loc in locs:
                await repo.update_last_alerted(loc, None)

            await send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: 🌧️ ฝนตกหนัก (Boost เมฆจริง)\n⏳ กำลังสร้างแจ้งเตือน...")

            from app.scheduler_tasks import check_rain_and_alert
            await check_rain_and_alert()
            
        elif command == "/devmock storm":
            await repo.set_mock_state(chat_id, "storm")

            # Reset cooldown สำหรับทุก location ของ user นี้ เพื่อให้ alert ยิงทันที
            locs = await repo.get_user_locations(chat_id)
            for loc in locs:
                await repo.update_last_alerted(loc, None)

            await send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: 🌪️ พายุจำลอง (สร้างเมฆปลอม 5 สี)\n⏳ กำลังสร้างแจ้งเตือน...")

            from app.scheduler_tasks import check_rain_and_alert
            await check_rain_and_alert()
            
        elif command == "/devmock clear":
            await repo.set_mock_state(chat_id, "clear")
            await send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: ☀️ ท้องฟ้าแจ่มใส\n⏳ กำลังตรวจสอบสภาพอากาศ...")
            
            from app.scheduler_tasks import check_rain_and_alert
            await check_rain_and_alert()
            
        elif command == "/devmock error":
            await repo.set_mock_state(chat_id, "error")
            await send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: ❌ เชื่อมต่อ API ล้มเหลวทั้งหมด\n⏳ กำลังส่งตำแหน่งเพื่อทดสอบ Fallback...")
            
            # Simulate a location update to trigger the fallback error message immediately
            locs = await repo.get_user_locations(chat_id)
            if locs:
                await process_telegram_location(chat_id, locs[0].latitude, locs[0].longitude, message_id_to_edit=None)
            else:
                await send_telegram_message(chat_id, "ไม่พบตำแหน่งที่บันทึกไว้ โปรดส่ง Location มาใหม่เพื่อทดสอบ error")

        elif command.startswith("/devmock scenario"):
            import json as _json
            from app.services.weather_manager import _parse_scenario_params

            params_str = command.removeprefix("/devmock scenario").strip()
            if not params_str:
                await send_telegram_message(
                    chat_id,
                    "🛠️ [DEV MOCK] ต้องระบุพารามิเตอร์ เช่น:\n"
                    "/devmock scenario rain_in:20 dbz:40 wind:60 wind_dir:N\n"
                    "พิมพ์ /devmock help เพื่อดูตัวเลือกทั้งหมด"
                )
                return

            scenario = _parse_scenario_params(params_str)

            # Extract optional loc:name parameter (not a scenario param)
            target_loc_name = scenario.pop("loc", None)
            if target_loc_name:
                target_loc_name = str(target_loc_name).lower()

            mock_state_json = _json.dumps(scenario, ensure_ascii=False)
            await repo.set_mock_state(chat_id, mock_state_json)

            # Reset cooldown — only for the target location (or all if not specified)
            locs = await repo.get_user_locations(chat_id)

            if target_loc_name:
                matched = [l for l in locs if l.name and l.name.lower() == target_loc_name]
                if not matched:
                    available = ", ".join([l.name for l in locs if l.name]) or "default"
                    await send_telegram_message(
                        chat_id,
                        f"⚠️ ไม่พบพิกัดชื่อ '{target_loc_name}'\nพิกัดที่มี: {available}"
                    )
                    return
                fire_locs = matched
            else:
                fire_locs = locs

            for loc in fire_locs:
                await repo.update_last_alerted(loc, None)

            # Build a human-readable summary of the scenario
            parts = []
            if target_loc_name:
                parts.append(f"📍 พิกัด: {target_loc_name.capitalize()}")
            if "rain_in" in scenario:
                parts.append(f"🕐 ฝนจะมาใน {scenario['rain_in']} นาที")
            if "rain_stopping" in scenario:
                parts.append(f"🌤 ฝนจะหยุดใน {scenario['rain_stopping']} นาที")
            if scenario.get("no_rain"):
                parts.append("☀️ ไม่มีฝน")
            if "dbz" in scenario:
                parts.append(f"📡 dBZ: {scenario['dbz']}")
            if "wind" in scenario:
                wind_dir = scenario.get("wind_dir", "?")
                parts.append(f"💨 ลม: {scenario['wind']} km/h จากทิศ {wind_dir}")
            if "growth" in scenario:
                sign = "+" if float(scenario["growth"]) >= 0 else ""
                parts.append(f"📈 Growth: {sign}{scenario['growth']}")
            if "clusters" in scenario:
                parts.append(f"☁️ เมฆ: {scenario['clusters']} ก้อน")

            summary = "\n".join(parts) if parts else "(ไม่มีพารามิเตอร์พิเศษ)"
            await send_telegram_message(
                chat_id,
                f"🛠️ [DEV MOCK] Scenario จำลอง:\n{summary}\n\n⏳ กำลังสร้างแจ้งเตือน..."
            )

            from app.scheduler_tasks import check_rain_and_alert, run_alert_for_locations
            if target_loc_name:
                await run_alert_for_locations(fire_locs)
            else:
                await check_rain_and_alert()

        elif command in ("/devmock help", "/devmock"):
            help_text = (
                "🛠️ <b>DEV MOCK — คำสั่งทั้งหมด</b>\n\n"
                "<b>โหมดพื้นฐาน:</b>\n"
                "<code>/devmock rain</code> — ฝนตกหนัก (Boost เมฆจริง)\n"
                "<code>/devmock storm</code> — พายุจำลอง 5 ก้อนเมฆ\n"
                "<code>/devmock clear</code> — ท้องฟ้าแจ่มใส\n"
                "<code>/devmock error</code> — API ล้มเหลวทั้งหมด\n"
                "<code>/devmock off</code> — ปิด mock mode\n\n"
                "<b>โหมด Parametric Scenario:</b>\n"
                "<code>/devmock scenario &lt;params&gt;</code>\n\n"
                "<b>พารามิเตอร์ที่รองรับ:</b>\n"
                "<code>rain_in:N</code> — ฝนจะมาใน N นาที\n"
                "<code>rain_stopping:N</code> — ฝนจะหยุดใน N นาที\n"
                "<code>no_rain</code> — ไม่มีฝน (ทดสอบลมอย่างเดียว)\n"
                "<code>dbz:N</code> — ความเข้มฝน dBZ (15–75, default 35)\n"
                "<code>wind:N</code> — ความเร็วลม km/h (default 20)\n"
                "<code>wind_dir:X</code> — ทิศลม: N/NE/E/SE/S/SW/W/NW\n"
                "<code>growth:N</code> — อัตราการเติบโต ±0.0–1.0\n"
                "<code>clusters:N</code> — จำนวนก้อนเมฆ 1–5 (default 1)\n"
                "<code>loc:NAME</code> — เจาะจงพิกัด (เช่น home, work)\n\n"
                "<b>ตัวอย่าง:</b>\n"
                "<code>/devmock scenario rain_in:20 dbz:40 wind:60 wind_dir:N</code>\n"
                "<code>/devmock scenario rain_in:10 dbz:55 growth:0.3 loc:work</code>\n"
                "<code>/devmock scenario rain_stopping:10 dbz:30 loc:home</code>\n"
                "<code>/devmock scenario no_rain wind:45 wind_dir:SE loc:home</code>\n\n"
                "<b>Dev/Test:</b>\n"
                "<code>/devmock check lat,lng</code> — เช็คฝน ณ พิกัดใดก็ได้\n"
                "<code>/devmock pixel lat,lng</code> — GPS → pixel (ทุก station)\n"
                "<code>/devmock pixel px,py skn240</code> — pixel → GPS\n"
                "<code>/devmock config</code> — ดู/ปรับ thresholds (cluster_min, min_dbz ฯลฯ)\n"
                "<code>/devmock flush_cache</code> — ล้าง in-memory cache (บังคับ GIF fallback)\n"
                "<code>/devmock flush_all_cache</code> — ล้าง in-memory + Firestore (GIF fallback ทันที)\n"
                "<code>/devmock cache_status</code> — ดูสถานะ cache ทุก layer"
            )
            await send_telegram_message(chat_id, help_text, parse_mode="HTML")


        elif command == "/devmock off":
            await repo.set_mock_state(chat_id, None)
            await send_telegram_message(chat_id, "🛠️ [DEV MOCK] ปิดใช้งานโหมดจำลองเรียบร้อยแล้ว\n⏳ กำลังส่งสถานะ All-Clear...")
            
            from app.scheduler_tasks import check_rain_and_alert
            await check_rain_and_alert()

        elif command == "/devmock flush_cache":
            from app.services.weather_manager import _GLOBAL_TMD_CACHE, _GLOBAL_TMD_LOCKS
            stations_cleared = list(_GLOBAL_TMD_CACHE.keys())
            _GLOBAL_TMD_CACHE.clear()
            stations_str = ", ".join(f"<code>{s}</code>" for s in stations_cleared) if stations_cleared else "<i>(ว่างอยู่แล้ว)</i>"
            msg = (
                "🗑️ <b>In-memory TMD cache cleared</b>\n\n"
                f"สถานีที่ล้าง: {stations_str}\n\n"
                "👉 ยิง <code>/devmock scenario ...</code> ต่อเพื่อทดสอบ GIF fallback\n"
                "<i>(ระบบจะโหลดจาก Firestore หรือ loop GIF แทน in-memory)</i>"
            )
            await send_telegram_message(chat_id, msg, parse_mode="HTML")

        elif command == "/devmock flush_all_cache":
            from app.services.weather_manager import _GLOBAL_TMD_CACHE
            _STATIONS = ["kkn240", "skn240", "kkn120"]

            # 1) Clear in-memory
            mem_before = list(_GLOBAL_TMD_CACHE.keys())
            _GLOBAL_TMD_CACHE.clear()

            # 2) Clear Firestore radar_latest_cache
            fs_cleared, fs_failed = [], []
            async with get_repo_context() as _repo:
                for st in _STATIONS:
                    try:
                        doc_ref = _repo.db.collection("radar_latest_cache").document(st)
                        await doc_ref.delete()
                        fs_cleared.append(st)
                    except Exception as _e:
                        fs_failed.append(f"{st}({_e})")

            mem_str = ", ".join(f"<code>{s}</code>" for s in mem_before) if mem_before else "<i>(ว่างอยู่แล้ว)</i>"
            fs_str  = ", ".join(f"<code>{s}</code>" for s in fs_cleared)
            fail_str = (f"\n⚠️ ล้มเหลว: {', '.join(fs_failed)}" if fs_failed else "")
            msg = (
                "🗑️ <b>Full cache cleared</b>\n\n"
                f"📦 In-Memory: {mem_str}\n"
                f"🗃️ Firestore: {fs_str}{fail_str}\n\n"
                "⚡ Cache phase รอบถัดไป (~20s) จะ bootstrap 6 frames อัตโนมัติ\n"
                "<i>(static frame ล่าสุด + GIF history → Firestore พร้อมใช้ทันที)</i>"
            )
            await send_telegram_message(chat_id, msg, parse_mode="HTML")


        elif command == "/devmock cache_status":
            from app.services.weather_manager import _GLOBAL_TMD_CACHE
            import time as _time
            from zoneinfo import ZoneInfo as _ZI
            _bkk = _ZI("Asia/Bangkok")


            lines = ["🗂️ <b>TMD Cache Status</b>\n"]

            # ── Layer 1: In-memory ─────────────────────────────
            lines.append("<b>📦 In-Memory (_GLOBAL_TMD_CACHE)</b>")
            if not _GLOBAL_TMD_CACHE:
                lines.append("  <i>(ว่าง)</i>")
            else:
                for st, entry in _GLOBAL_TMD_CACHE.items():
                    n_frames  = len(entry[0]) if entry[0] else 0
                    cached_at = entry[2]
                    src       = entry[4] if len(entry) > 4 else "?"
                    ts_list   = list(entry[6]) if len(entry) > 6 else []
                    age_s     = int(_time.time() - cached_at)
                    ttl_left  = max(0, 600 - age_s)
                    latest_bkk = (
                        __import__("datetime").datetime.fromtimestamp(ts_list[-1], _bkk).strftime("%H:%M")
                        if ts_list else "?"
                    )
                    lines.append(
                        f"  <code>{st}</code> {n_frames}f  src=<code>{src}</code>"
                        f"  latest={latest_bkk} BKK  age={age_s}s  TTL={ttl_left}s"
                    )

            # ── Layer 2: Firestore station cache ───────────────
            lines.append("\n<b>🗃️ Firestore (radar_latest_cache)</b>")
            async with get_repo_context() as _repo:
                for st in ["kkn240", "skn240", "kkn120"]:
                    c = await _repo.get_latest_radar_cache(st)
                    if c and c.get("frames"):
                        fs = sorted(c["frames"], key=lambda x: x["timestamp"])
                        latest_bkk = (
                            __import__("datetime").datetime.fromtimestamp(fs[-1]["timestamp"], _bkk).strftime("%H:%M")
                        )
                        lines.append(f"  <code>{st}</code> {len(fs)}f  latest={latest_bkk} BKK")
                    else:
                        lines.append(f"  <code>{st}</code> <i>(ว่าง)</i>")

            await send_telegram_message(chat_id, "\n".join(lines), parse_mode="HTML")

        # ── /devmock check lat,lng ─────────────────────────────────────────────
        elif command.startswith("/devmock check"):
            import re as _re
            args = command.removeprefix("/devmock check").strip()
            coords_m = _re.search(r'([+-]?\d+\.?\d*)[,\s]+([+-]?\d+\.?\d*)', args)
            if not coords_m:
                await send_telegram_message(
                    chat_id,
                    "🛠️ ใช้: <code>/devmock check lat,lng</code>\n"
                    "เช่น: <code>/devmock check 18.665,101.861</code>",
                    parse_mode="HTML",
                )
                return
            chk_lat = float(coords_m.group(1))
            chk_lng = float(coords_m.group(2))
            await send_telegram_message(
                chat_id,
                f"🛠️ กำลังเช็คฝน ณ พิกัด <code>{chk_lat:.5f}, {chk_lng:.5f}</code>…",
                parse_mode="HTML",
            )
            await process_telegram_location(chat_id, chk_lat, chk_lng, message_id_to_edit=None)

        # ── /devmock pixel lat,lng  or  /devmock pixel px,py station ──────────
        elif command.startswith("/devmock pixel"):
            import re as _re
            from app.services.tmd_radar_config import STATIONS
            from app.services.tmd_radar_processor import TMDRadarProcessor as _TRP
            args = command.removeprefix("/devmock pixel").strip()
            # Detect mode: if values have '.', treat as lat/lng; else as pixel coords
            nums = _re.findall(r'[+-]?\d+\.?\d*', args)
            station_hint = _re.search(r'(kkn\d+|skn\d+)', args.lower())
            st_code = station_hint.group(1) if station_hint else None

            if len(nums) < 2:
                await send_telegram_message(
                    chat_id,
                    "🛠️ ใช้:\n"
                    "<code>/devmock pixel lat,lng</code> — แปลง GPS → pixel\n"
                    "<code>/devmock pixel px,py station</code> — แปลง pixel → GPS\n"
                    "เช่น: <code>/devmock pixel 18.665,101.861</code>\n"
                    "เช่น: <code>/devmock pixel 300,200 skn240</code>",
                    parse_mode="HTML",
                )
                return

            is_latlng = '.' in nums[0] or '.' in nums[1]
            lines_px = [f"🗺️ <b>Pixel Coordinate Tool</b>\n"]
            if is_latlng:
                lat_v = float(nums[0])
                lng_v = float(nums[1])
                lines_px.append(f"📍 GPS: <code>{lat_v:.5f}, {lng_v:.5f}</code>\n")
                for sc, cfg in STATIONS.items():
                    try:
                        proc = _TRP(sc)
                        px_loop, py_loop = proc.latlng_to_pixel(lat_v, lng_v, is_loop=True)
                        px_stat, py_stat = proc.latlng_to_pixel(lat_v, lng_v, is_loop=False)
                        if px_loop is None:
                            lines_px.append(f"  <code>{sc}</code>: นอก bbox")
                            continue
                        lines_px.append(
                            f"  <code>{sc}</code>: loop=<code>({px_loop},{py_loop})</code>  static=<code>({px_stat},{py_stat})</code>"
                        )
                    except Exception:
                        pass
            else:
                # Pixel → lat/lng
                px_v = int(float(nums[0]))
                py_v = int(float(nums[1]))
                target_st = st_code or "skn240"
                lines_px.append(f"📍 Pixel: <code>({px_v}, {py_v})</code>  station=<code>{target_st}</code>\n")
                try:
                    proc = _TRP(target_st)
                    cfg = proc.config
                    bbox = cfg.bbox
                    # Reverse loop mapping
                    cw, ch = cfg.loop_crop_width, cfg.loop_crop_height
                    x_pct = (px_v - cfg.loop_crop_x) / cw
                    y_pct = (py_v - cfg.loop_crop_y) / ch
                    lng_v = x_pct * (bbox.lng_max - bbox.lng_min) + bbox.lng_min
                    lat_v = bbox.lat_max - y_pct * (bbox.lat_max - bbox.lat_min)
                    lines_px.append(f"  → GPS (loop): <code>{lat_v:.5f}, {lng_v:.5f}</code>")
                    # Also show reverse for static
                    cw2, ch2 = cfg.static_crop_width, cfg.static_crop_height
                    x_pct2 = (px_v - cfg.static_crop_x) / cw2
                    y_pct2 = (py_v - cfg.static_crop_y) / ch2
                    lng_v2 = x_pct2 * (bbox.lng_max - bbox.lng_min) + bbox.lng_min
                    lat_v2 = bbox.lat_max - y_pct2 * (bbox.lat_max - bbox.lat_min)
                    lines_px.append(f"  → GPS (static): <code>{lat_v2:.5f}, {lng_v2:.5f}</code>")
                except Exception as _e:
                    lines_px.append(f"  ❌ Error: {_e}")
            await send_telegram_message(chat_id, "\n".join(lines_px), parse_mode="HTML")

        # ── /devmock config [key:val ...] ──────────────────────────────────────
        elif command.startswith("/devmock config"):
            from app.services.weather_manager import _DEV_CONFIG
            args = command.removeprefix("/devmock config").strip()
            if not args:
                # Show current config
                lines_cfg = ["🛠️ <b>Dev Config (ค่าปัจจุบัน)</b>\n"]
                for k, v in _DEV_CONFIG.items():
                    lines_cfg.append(f"  <code>{k}</code> = <b>{v}</b>")
                lines_cfg.append(
                    "\n<b>ปรับได้:</b>\n"
                    "<code>/devmock config cluster_min:1</code>\n"
                    "<code>/devmock config search_radius:120</code>\n"
                    "<code>/devmock config min_dbz:5</code>\n"
                    "<code>/devmock config dot_threshold:0.3</code>\n"
                    "<code>/devmock config flow_mode:average</code>\n"
                    "<code>/devmock config decay_enabled:false</code>\n"
                    "<code>/devmock config prediction_steps:10</code>\n"
                    "<code>/devmock config reset</code> — คืนค่า default"
                )
                await send_telegram_message(chat_id, "\n".join(lines_cfg), parse_mode="HTML")
                return

            if args.strip() == "reset":
                _DEV_CONFIG["cluster_min"]   = 3
                _DEV_CONFIG["search_radius"] = 80
                _DEV_CONFIG["min_dbz"]       = 10.0
                _DEV_CONFIG["dot_threshold"] = 0.5
                _DEV_CONFIG["flow_mode"]     = "average"
                _DEV_CONFIG["hit_radius"]    = 8
                _DEV_CONFIG["verbose"]       = False
                _DEV_CONFIG["decay_enabled"] = True
                _DEV_CONFIG["prediction_steps"] = 7
                await repo.set_global_dev_config(_DEV_CONFIG)
                await send_telegram_message(chat_id, "🛠️ Dev Config รีเซ็ตเป็นค่า default แล้วครับ ✅")
                return

            import re as _re
            changed = []
            for pair in _re.findall(r'(\w+)\s*:\s*([a-zA-Z0-9_.-]+)', args):
                key, raw_val = pair
                if key not in _DEV_CONFIG:
                    continue
                try:
                    cur = _DEV_CONFIG[key]
                    if isinstance(cur, bool):
                        new_val = raw_val.lower() in ("true", "1", "yes")
                    elif isinstance(cur, (int, float)):
                        new_val = type(cur)(raw_val)
                    else:
                        new_val = raw_val
                    _DEV_CONFIG[key] = new_val
                    changed.append(f"  <code>{key}</code>: {cur} → <b>{new_val}</b>")
                except Exception:
                    pass
            if changed:
                await repo.set_global_dev_config(_DEV_CONFIG)
                await send_telegram_message(
                    chat_id,
                    "🛠️ <b>Dev Config อัพเดต</b>\n" + "\n".join(changed),
                    parse_mode="HTML",
                )
            else:
                await send_telegram_message(
                    chat_id,
                    "⚠️ ไม่พบ key ที่รู้จัก\nKey ที่รองรับ: <code>" + ", ".join(_DEV_CONFIG.keys()) + "</code>",
                    parse_mode="HTML",
                )

        # ── /devmock cleancache [station] ──────────────────────────────────────
        elif command.startswith("/devmock cleancache"):
            args = command.removeprefix("/devmock cleancache").strip()
            station = args if args else "skn240"
            
            from app.services.weather_manager import _GLOBAL_TMD_CACHE
            _GLOBAL_TMD_CACHE.pop(station, None)
            await repo.set_latest_radar_cache(station, [])
            
            await send_telegram_message(chat_id, f"🔄 ล้าง Cache ของสถานี {station} สำเร็จ!\nการเช็คฝนรอบถัดไปจะดึงภาพใหม่ล่าสุดจาก TMD ครับ")

        # ── /devmock fetch_latest [station] ────────────────────────────────────
        elif command.startswith("/devmock fetch_latest"):
            args = command.removeprefix("/devmock fetch_latest").strip()
            station = args if args else "skn240"
            
            await send_telegram_message(chat_id, f"🔄 กำลังเช็คภาพล่าสุดแบบเดี่ยวของสถานี {station}...")
            
            from app.services.weather_manager import _GLOBAL_TMD_CACHE, _DEV_CONFIG
            from app.services.tmd_radar_processor import TMDRadarProcessor
            from app.services.ocr_service import OCRService
            import time
            from datetime import datetime, timezone
            import cv2
            
            cached_data = _GLOBAL_TMD_CACHE.get(station)
            if not cached_data or not cached_data[0]:
                from app.services.weather_manager import WeatherManager
                wm = WeatherManager()
                processor = TMDRadarProcessor(station)
                cached_data = await wm.load_persistent_cache_to_memory(station, processor)
                
            if not cached_data or not cached_data[0]:
                await send_telegram_message(chat_id, f"❌ ไม่มี Cache เก่าสำหรับ {station} (ในฐานข้อมูลก็ไม่มีเช่นกัน ต้องใช้ /rain ก่อนครับ)")
                return
                
            frames = list(cached_data[0])
            frame_timestamps = list(cached_data[6]) if len(cached_data) > 6 else []
            
            if not frame_timestamps:
                await send_telegram_message(chat_id, f"❌ ไม่มีข้อมูล Timestamp ใน Cache ของ {station}")
                return
                
            processor = TMDRadarProcessor(station)
            new_frame = await processor.decode_static_frame()
            if new_frame is None:
                await send_telegram_message(chat_id, f"❌ โหลดภาพล่าสุด (Static) จาก TMD ไม่สำเร็จ")
                return
                
            target_h, target_w = frames[-1].shape[:2]
            if new_frame.shape[:2] != (target_h, target_w):
                new_frame = cv2.resize(new_frame, (target_w, target_h), interpolation=cv2.INTER_NEAREST)
                
            ocr_svc = OCRService()
            new_ts = await ocr_svc.get_frame_timestamp(new_frame, fallback_ts=int(time.time()))
            
            if new_ts is None:
                await send_telegram_message(chat_id, f"❌ อ่านเวลาจากภาพใหม่ไม่สำเร็จ")
                return
                
            # Check if the retrieved static image is outdated (older than 2 hours)
            now_ts = time.time()
            static_age_minutes = (now_ts - new_ts) / 60.0
            if static_age_minutes > 120.0:
                await send_telegram_message(
                    chat_id, 
                    f"⚠️ ตรวจพบภาพนิ่ง (Static) ล้าหลังเกิน 2 ชั่วโมง ({static_age_minutes:.0f} นาที) ทำการล้าง Cache เพื่อบังคับดึง Loop GIF ใหม่ครับ"
                )
                _GLOBAL_TMD_CACHE.pop(station, None)
                async with get_repo_context() as repo:
                    await repo.set_latest_radar_cache(station, [])
                return
                
            if new_ts <= frame_timestamps[-1]:
                await send_telegram_message(chat_id, f"⚠️ ภาพล่าสุดในเว็บ ({datetime.fromtimestamp(new_ts).strftime('%H:%M')}) ยังไม่ใหม่กว่าที่เรามีอยู่ ({datetime.fromtimestamp(frame_timestamps[-1]).strftime('%H:%M')})")
                return
                
            gap_minutes = (new_ts - frame_timestamps[-1]) / 60.0
            if gap_minutes > 30.0:
                await send_telegram_message(chat_id, f"⚠️ ภาพใหม่ห่างจากภาพเดิมเกิน 30 นาที ({gap_minutes:.0f} นาที) ทำการล้าง Cache เพื่อบังคับดึง Loop GIF ใหม่ครับ")
                _GLOBAL_TMD_CACHE.pop(station, None)
                async with get_repo_context() as repo:
                    await repo.set_latest_radar_cache(station, [])
                return
                
            # Append new frame
            frames.append(new_frame)
            frame_timestamps.append(new_ts)
            
            if len(frames) > 6:
                frames = frames[-6:]
                frame_timestamps = frame_timestamps[-6:]
                
            if _DEV_CONFIG.get("flow_mode", "latest") == "average":
                flow = processor.calculate_average_optical_flow(frames)
            else:
                flow = processor.calculate_optical_flow(frames)
                
            data_gap_minutes = (frame_timestamps[-1] - frame_timestamps[-2]) / 60.0
            new_dt = datetime.fromtimestamp(new_ts, timezone.utc)
            
            _GLOBAL_TMD_CACHE[station] = (
                frames, new_dt, time.time(), flow,
                "static_append", data_gap_minutes, frame_timestamps
            )
            
            # Persist to DB
            saved_frames = []
            for f_img, f_ts in zip(frames, frame_timestamps):
                if f_img.shape[0] != 800 or f_img.shape[1] != 800:
                    f_img_r = cv2.resize(f_img, (800, 800), interpolation=cv2.INTER_NEAREST)
                else:
                    f_img_r = f_img
                is_ok, buf = cv2.imencode(".png", cv2.cvtColor(f_img_r, cv2.COLOR_RGB2BGR))
                if is_ok:
                    f_url = await processor.save_polled_frame(buf.tobytes())
                    saved_frames.append({"url": f_url, "timestamp": f_ts})
            
            if saved_frames:
                await repo.set_latest_radar_cache(station_code=station, frames=saved_frames)
                
                await send_telegram_message(chat_id, f"✅ ต่อภาพล่าสุด ({new_dt.strftime('%H:%M')}) สำเร็จ! อัพเดต Cache และ Optical Flow เรียบร้อยครับ")

        # ── /devmock visualize_flow [station] ──────────────────────────────────
        elif command.startswith("/devmock visualize_flow"):
            args = command.removeprefix("/devmock visualize_flow").strip()
            station = args if args else "skn240"
            await send_telegram_message(
                chat_id, 
                f"🛠️ กำลังสร้างภาพ Debug Optical Flow สำหรับสถานี {station}...", 
                parse_mode="HTML"
            )
            
            from app.services.tmd_radar_processor import TMDRadarProcessor
            try:
                processor = TMDRadarProcessor(station)
                frames_data, _, _ = await processor.fetch_loop_gif_and_extract_frames()
                if not frames_data or len(frames_data) < 2:
                    await send_telegram_message(chat_id, "❌ ดึงภาพจาก TMD ไม่สำเร็จ หรือมีน้อยกว่า 2 เฟรม")
                    return
                    
                import cv2
                import numpy as np
                import asyncio
                
                prev_frame = cv2.resize(frames_data[-2], (800, 800), interpolation=cv2.INTER_NEAREST)
                curr_frame = cv2.resize(frames_data[-1], (800, 800), interpolation=cv2.INTER_NEAREST)
                
                # Resize all frames to 800x800 for the debug image generator
                resized_frames = [cv2.resize(f, (800, 800), interpolation=cv2.INTER_NEAREST) for f in frames_data]
                
                from app.services.weather_manager import _DEV_CONFIG
                
                images = await asyncio.to_thread(
                    processor.generate_multiframe_flow_debug_images,
                    resized_frames, 400, 400, _DEV_CONFIG.get("min_dbz", 10.0), _DEV_CONFIG.get("flow_mode", "latest")
                )
                
                from app.services.telegram import send_telegram_photo
                await send_telegram_photo(chat_id, images["rain_mask"], "debug_1_rain_mask.png")
                await send_telegram_photo(chat_id, images["flow_hsv"], "debug_2_flow_hsv.png")
                await send_telegram_photo(chat_id, images["flow_grid"], "debug_3_flow_grid.png")
                await send_telegram_photo(chat_id, images["clusters"], "debug_4_clusters.png")
                
                await send_telegram_message(chat_id, "✅ ส่งภาพ Debug ครบแล้วครับ")
            except Exception as e:
                import traceback
                logger.error(f"visualize_flow error: {e}\n{traceback.format_exc()}")
                await send_telegram_message(chat_id, f"❌ Error: {e}")
            return


async def handle_rain_command(chat_id: int, command: str, show_advanced: bool = False):
    import re
    coords_match = re.search(r'([+-]?\d+\.\d+)[,\s]+([+-]?\d+\.\d+)', command)
    custom_lat = None
    custom_lng = None
    if coords_match:
        try:
            custom_lat = float(coords_match.group(1))
            custom_lng = float(coords_match.group(2))
            command = command.replace(coords_match.group(0), "").strip()
        except ValueError:
            pass

    parts = command.strip().split()
    force_provider = None
    target_location_name = None
    
    known_providers = ["tmd-radar", "tomorrow", "rainbow-local", "rainbow-global", "xweather", "open-meteo", "tmd", "kkn120", "kkn240", "skn240"]
    provider_aliases = {"tmd": "tmd-radar"}
    
    if len(parts) > 1:
        part1 = parts[1].lower()
        if part1 in known_providers:
            force_provider = part1
            if len(parts) > 2:
                target_location_name = parts[2].lower()
        else:
            target_location_name = part1
            if len(parts) > 2 and parts[2].lower() in known_providers:
                force_provider = parts[2].lower()
                
    if force_provider in provider_aliases:
        force_provider = provider_aliases[force_provider]
    
    loc = None
    if custom_lat is not None and custom_lng is not None:
        from app.models import UserLocation
        loc = UserLocation(
            chat_id=chat_id,
            latitude=custom_lat,
            longitude=custom_lng,
            name=f"{custom_lat}, {custom_lng}"
        )
    else:
        async with get_repo_context() as repo:
            locs = await repo.get_user_locations(chat_id)
            
        if not locs:
            await send_telegram_message(chat_id, "⚠️ ไม่พบพิกัดที่บันทึกไว้ กรุณาส่ง Location ให้บอทก่อนครับ")
            return
            
        if target_location_name == "all":
            await send_telegram_message(chat_id, f"⏳ กำลังตรวจสอบสภาพอากาศทั้งหมด {len(locs)} จุด...")
            for l in locs:
                loc_display = l.name.capitalize() if l.name else "Default"
                msg_text = f"⏳ กำลังตรวจสอบสภาพอากาศที่ '{loc_display}'..."
                loading_msg_id = await send_telegram_message_return_id(chat_id, msg_text)
                await process_telegram_location(
                    chat_id, lat=l.latitude, lng=l.longitude,
                    force_endpoint=force_provider, message_id_to_edit=loading_msg_id,
                    show_advanced=show_advanced, location_name=loc_display
                )
            return

        if target_location_name:
            for l in locs:
                if (l.name and l.name.lower() == target_location_name) or (target_location_name == "default" and l.name is None):
                    loc = l
                    break
            if not loc:
                available_locs = ", ".join([l.name for l in locs if l.name])
                await send_telegram_message(chat_id, f"⚠️ ไม่พบพิกัดชื่อ '{target_location_name}'\nพิกัดที่มี: {available_locs or 'default'}")
                return
        else:
            loc = locs[0]
        
    loc_display = loc.name.capitalize() if loc.name else "ระบบอัตโนมัติ"
    msg_text = f"⏳ กำลังตรวจสอบสภาพอากาศที่ '{loc_display}' "
    if force_provider:
        msg_text += f"จาก {force_provider}..."
    else:
        msg_text += "..."
        
    loading_msg_id = await send_telegram_message_return_id(chat_id, msg_text)
    
    await process_telegram_location(
        chat_id, lat=loc.latitude, lng=loc.longitude,
        force_endpoint=force_provider, message_id_to_edit=loading_msg_id,
        show_advanced=show_advanced, location_name=loc_display
    )


@router.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        return await _telegram_webhook_impl(request, background_tasks)
    except Exception as e:
        logger.exception(f"Error in telegram_webhook: {e}")
        try:
            payload = await request.json()
            chat_id = payload.get("message", {}).get("chat", {}).get("id")
        except Exception:
            chat_id = None
        if chat_id:
            from app.services.telegram import send_telegram_message
            await send_telegram_message(chat_id, "⚠️ ระบบยุ่งชั่วคราว กรุณาลองใหม่อีกครั้ง")
        return {"status": "error", "detail": str(e)}

async def _telegram_webhook_impl(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()

    if "callback_query" in payload:
        await handle_callback_query(payload["callback_query"])
        return {"status": "ok"}

    if "message" in payload:
        message = payload["message"]
        chat_id = message.get("chat", {}).get("id")
        date_ts = message.get("date", 0)

        # Handle pending updates: ignore messages older than 2 minutes (120 seconds)
        current_ts = datetime.now(timezone.utc).timestamp()
        if date_ts > 0 and (current_ts - date_ts) > 120:
            logger.warning(f"[WEBHOOK] Ignoring stale message from chat_id={chat_id} (age: {current_ts - date_ts:.1f}s)")
            return {"status": "ok", "ignored": "stale"}

        if "location" in message and chat_id:
            location = message["location"]
            lat = location.get("latitude")
            lng = location.get("longitude")

            if lat and lng:
                # Remember this chat's most recently pinned coordinate so that
                # a subsequent /lock (with no saved-location name) targets this
                # spot instead of falling back to the saved "home" location.
                LAST_PINNED_LOCATION[chat_id] = (float(lat), float(lng))

                # ส่งข้อความตอบกลับทันทีเพื่อให้ผู้ใช้รู้ว่าบอทได้รับข้อมูลแล้ว
                loading_msg_id = await send_telegram_message_return_id(
                    chat_id,
                    "⏳ กำลังประมวลผลเรดาร์และพยากรณ์อากาศ กรุณารอสักครู่..."
                )
                from app.services.cloud_tasks import CloudTasksService
                tasks_svc = CloudTasksService()
                payload = {
                    "chat_id": chat_id, "lat": lat, "lng": lng,
                    "message_id_to_edit": loading_msg_id
                }
                if not await tasks_svc.enqueue_task("worker/process-telegram-location", payload):
                    # ส่ง message_id ไปให้ background task เพื่อ edit ต่อเมื่อเสร็จ
                    background_tasks.add_task(
                        process_telegram_location, chat_id, lat, lng,
                        None, loading_msg_id
                    )
                return {"status": "ok"}

        text = message.get("text", "")
        username = message.get("from", {}).get("username", "")
        logger.info(f"[WEBHOOK] Received text='{text}' chat_id={chat_id} username={username}")

        from app.services.cloud_tasks import CloudTasksService
        tasks_svc = CloudTasksService()

        if text.startswith("/mylocation") and chat_id:
            if not await tasks_svc.enqueue_task("worker/handle-mylocation", {"chat_id": chat_id}):
                background_tasks.add_task(handle_mylocation_command, chat_id)
            return {"status": "ok"}

        if text.startswith("/radar") and chat_id:
            if not await tasks_svc.enqueue_task("worker/handle-radar", {"chat_id": chat_id}):
                background_tasks.add_task(handle_radar_command, chat_id)
            return {"status": "ok"}
            
        if text.startswith("/bypass_logout") and chat_id:
            async def _do_logout():
                async with get_repo_context() as repo:
                    await repo.delete_admin_bypass(chat_id)
                log_audit_event("bypass_logout", chat_id, username, {})
                await send_telegram_message(chat_id, "ออกจากระบบ Emergency Admin Bypass เรียบร้อยแล้ว")
            background_tasks.add_task(_do_logout)
            return {"status": "ok"}

        if text.startswith("/bypass ") and chat_id:
            password = text.removeprefix("/bypass ").strip()
            async def _do_login():
                import os
                actual_pass = os.getenv("ADMIN_BYPASS_PASSWORD")
                if actual_pass and password == actual_pass:
                    async with get_repo_context() as repo:
                        await repo.save_admin_bypass(chat_id)
                    log_audit_event("bypass_login_success", chat_id, username, {})
                    await send_telegram_message(chat_id, "✅ ยืนยันรหัสผ่านถูกต้อง! เปิดใช้งาน Emergency Admin Bypass (1 ชั่วโมง)")
                else:
                    log_audit_event("bypass_login_failed", chat_id, username, {})
                    await send_telegram_message(chat_id, "❌ รหัสผ่านไม่ถูกต้อง")
            background_tasks.add_task(_do_login)
            return {"status": "ok"}

        if text.startswith("/lock ") and chat_id:
            background_tasks.add_task(handle_lock_command, chat_id, text)
            return {"status": "ok"}
            
        if text.startswith("/unlock") and chat_id:
            background_tasks.add_task(handle_unlock_command, chat_id, text)
            return {"status": "ok"}

        if text.startswith(("/rain", "/check", "/devmock", "/tmd_fallback", "/metrics", "/setbudget")) and chat_id:
            import os
            is_dev_env = os.getenv("ENVIRONMENT", "production").lower() == "development"
            if not is_dev_env:
                has_access = await check_admin_access(chat_id)
                if not has_access:
                    background_tasks.add_task(
                        send_telegram_message, chat_id, 
                        "⚠️ ขออภัยครับ คำสั่งนี้ไม่เปิดให้ใช้งานในระบบปัจจุบัน"
                    )
                    return {"status": "ok"}

        if text.startswith("/metrics") and chat_id:
            background_tasks.add_task(handle_metrics_command, chat_id, text.strip(), username)
            return {"status": "ok"}

        if text.startswith("/setbudget") and chat_id:
            background_tasks.add_task(handle_setbudget_command, chat_id, text.strip(), username)
            return {"status": "ok"}

        if text.startswith("/rain_pro") and chat_id:
            if not await tasks_svc.enqueue_task("worker/handle-rain", {"chat_id": chat_id, "command": text, "show_advanced": True}):
                background_tasks.add_task(handle_rain_command, chat_id, text, show_advanced=True)
            return {"status": "ok"}

        if text.startswith("/rain") and chat_id:
            if not await tasks_svc.enqueue_task("worker/handle-rain", {"chat_id": chat_id, "command": text}):
                background_tasks.add_task(handle_rain_command, chat_id, text)
            return {"status": "ok"}

        if text.startswith("/devmock") and chat_id:
            if not await tasks_svc.enqueue_task("worker/handle-devmock", {"chat_id": chat_id, "command": text.strip()}):
                background_tasks.add_task(handle_devmock_command, chat_id, text.strip())
            return {"status": "ok"}

        if text.startswith("/tmd_fallback") and chat_id:
            background_tasks.add_task(handle_tmd_fallback_command, chat_id, text.strip(), username)
            return {"status": "ok"}

        # /check — shorthand alias for /rain tmd-radar (for manual testing)
        if text.strip() == "/check" and chat_id:
            logger.info(f"[WEBHOOK] /check received from chat_id={chat_id}, routing to handle_rain_command with 'tmd-radar'")
            if not await tasks_svc.enqueue_task("worker/handle-rain", {"chat_id": chat_id, "command": "/rain tmd-radar"}):
                background_tasks.add_task(handle_rain_command, chat_id, "/rain tmd-radar")
            return {"status": "ok"}

        logger.debug(f"[WEBHOOK] Unrecognized command or text, returning ignored. text='{text}'")

    return {"status": "ignored"}
