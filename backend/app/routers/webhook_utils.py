import os
import json
import logging
from datetime import datetime, timezone

from contextlib import asynccontextmanager

@asynccontextmanager
async def get_repo_context():
    from app.dependencies import get_repo_context as _get_repo_context
    async with _get_repo_context() as repo:
        yield repo
from app.services import telegram

logger = logging.getLogger(__name__)

LAST_ACTIVE_LOCATION: dict[int, str] = {}

# Most recently pinned/sent Telegram location per chat (lat, lng).
# Populated whenever the user sends a location via Telegram, and consumed by
# /lock (and the inline lock button) when no saved-location name is supplied,
# so that locking targets the spot the user just shared instead of "home".
LAST_PINNED_LOCATION: dict[int, tuple[float, float]] = {}

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
    is_prod = os.getenv("ENVIRONMENT", "production").lower() != "development"

    async with get_repo_context() as repo:
        if await repo.has_active_admin_bypass(chat_id):
            return True
            
    # ถ้าอยู่ใน Development mode, Developer เข้าถึงได้เลยโดยไม่ต้อง bypass
    if str(chat_id) in telegram.DEVELOPER_CHAT_IDS and not is_prod:
        return True
        
    return False

async def _reply(
    chat_id: int,
    text: str,
    message_id_to_edit: int = None,
    reply_markup: dict = None,
) -> None:
    """Send or edit a Telegram message depending on whether we have a loading message."""
    if message_id_to_edit:
        await telegram.edit_telegram_message(chat_id, message_id_to_edit, text, reply_markup)
    else:
        await telegram.send_telegram_message(chat_id, text, reply_markup)

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
