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

def get_gcp_project_id() -> str:
    """Return unified GCP Project ID with standard fallbacks."""
    return os.getenv("GCP_PROJECT_ID", os.getenv("GCP_PROJECT", os.getenv("GOOGLE_CLOUD_PROJECT", "fonmayang")))

def get_gcp_region() -> str:
    """Return GCP region/location with fallback."""
    return os.getenv("GCP_LOCATION", "asia-southeast1")

def get_gcp_access_token() -> str:
    """Get GCP access token using default credentials."""
    import google.auth
    from google.auth.transport.requests import Request as GoogleAuthRequest

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh(GoogleAuthRequest())
    return credentials.token

DEFAULT_SCHEDULER_JOBS = [
    {"job_name": "fonmayang-check-rain", "state": "ENABLED"},
    {"job_name": "fonmayang-fetch-radar", "state": "ENABLED"},
    {"job_name": "fonmayang-disasters-freq", "state": "PAUSED"},
    {"job_name": "fonmayang-disasters-infreq", "state": "PAUSED"},
    {"job_name": "fonmayang-sync-burn-rate", "state": "ENABLED"},
]

def load_scheduler_jobs_config() -> list[dict]:
    """
    Load Cloud Scheduler configuration from backend/config/schedulers.json
    Fallback to DEFAULT_SCHEDULER_JOBS if missing or corrupted.
    """
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../config/schedulers.json")
    if os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                jobs_config = json.load(f)
                if isinstance(jobs_config, list) and jobs_config:
                    return jobs_config
        except Exception as e:
            logger.error(f"Failed to read schedulers.json: {e}")
    return list(DEFAULT_SCHEDULER_JOBS)

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


from dataclasses import dataclass, field
from typing import List, Optional, Any

@dataclass
class ForecastMediaItem:
    media_type: str  # "photo", "document", "animation"
    data: bytes
    filename: str
    mime_type: str = "image/png"


@dataclass
class FormattedForecastResponse:
    text: str
    actual_endpoint: str
    eta_minutes: Optional[int]
    advanced_text: Optional[str] = None
    media_items: List[ForecastMediaItem] = field(default_factory=list)


def _build_advanced_text(
    advanced_data: Optional[dict] = None,
    advisories: Optional[list] = None,
    lightning: Optional[dict] = None,
    stormcells: Optional[list] = None,
    stormcell: Optional[dict] = None,
) -> str:
    """
    สร้างข้อความเตือนภัยขั้นสูง (advisories, lightning, stormcell)
    ใช้ร่วมกันทั้ง Telegram และ LINE
    """
    if advanced_data:
        advisories = advanced_data.get("advisories", [])
        lightning = advanced_data.get("lightning")
        stormcell = advanced_data.get("stormcell") or (advanced_data.get("stormcells", [None])[0] if advanced_data.get("stormcells") else None)
    elif stormcells and not stormcell:
        stormcell = stormcells[0] if len(stormcells) > 0 else None

    has_advisory = bool(advisories and len(advisories) > 0)
    has_lightning = bool(
        lightning and isinstance(lightning, dict) and lightning.get("detected", False)
    )
    has_stormcell = bool(stormcell)

    if has_advisory or has_lightning or has_stormcell:
        adv_text = "🚨 *ข้อมูลเตือนภัยขั้นสูงรอบตัวคุณ*\n\n"
        if has_advisory:
            for adv in advisories:
                adv_text += f"⚠️ ประกาศเตือนภัย: {adv.get('name', '')}\n"
            adv_text += "\n"
        if has_lightning:
            dist = lightning.get('distance_km', 0) if isinstance(lightning, dict) else 0
            adv_text += f"⚡ ฟ้าผ่าระยะใกล้สุด: {dist:.1f} กม.\n\n"
        if has_stormcell:
            dist_km = stormcell.get('distance_km')
            if dist_km is None:
                adv_text += f"🌪️ แนวโน้มกลุ่มฝน/ลม (Contingency):\n"
                adv_text += f"   - ทิศทาง: {stormcell.get('direction', 'N/A')}\n"
                adv_text += f"   - ความเร็วลม: {stormcell.get('speed_kmh', 0):.1f} km/h\n\n"
                adv_text += "ℹ️ ข้อมูลขั้นสูงจาก Open-Meteo (Fallback)"
            else:
                adv_text += f"🌪️ ตรวจพบกลุ่มพายุ: ระยะห่าง {dist_km:.1f} กม.\n"
                adv_text += f"   - ทิศทาง: {stormcell.get('direction', 'N/A')}\n"
                adv_text += f"   - ความเร็ว: {stormcell.get('speed_kmh', 0):.1f} km/h\n"
                adv_text += f"   - ความรุนแรงสูงสุด (dBZ): {stormcell.get('max_dbz', 0)}\n\n"
                adv_text += "ℹ️ ข้อมูลขั้นสูงจาก Xweather"
        elif has_advisory or has_lightning:
            adv_text += "ℹ️ ข้อมูลขั้นสูงจาก Xweather"
        return adv_text

    return "ℹ️ ข้อมูลเตือนภัยขั้นสูง: ไม่พบประกาศเตือนภัย พายุ หรือฟ้าผ่าในระยะใกล้"


def extract_forecast_media(
    result: dict,
    cmd_name: str = "/rain",
    show_advanced: bool = False,
    location_name: str = "default"
) -> List[ForecastMediaItem]:
    """
    สกัด media bytes จาก result dict ของ WeatherManager เป็นรายการ ForecastMediaItem
    ที่ใช้ร่วมกันได้ทั้ง Telegram และ LINE
    """
    media_items: List[ForecastMediaItem] = []
    
    static_bytes = result.get("radar_static_bytes")
    tracking_bytes = result.get("radar_tracking_bytes")
    timeline_bytes = result.get("rain_timeline_bytes")
    multiframe_bytes = result.get("radar_multiframe_bytes")
    hq_gif_bytes = result.get("radar_hq_gif_bytes")
    gif_bytes = result.get("radar_gif_bytes")

    if show_advanced or cmd_name == "/rain_pro":
        if tracking_bytes:
            media_items.append(ForecastMediaItem("photo", tracking_bytes, "radar_tracking.png", "image/png"))
        if static_bytes:
            media_items.append(ForecastMediaItem("photo", static_bytes, "radar_latest.png", "image/png"))
        if timeline_bytes:
            media_items.append(ForecastMediaItem("photo", timeline_bytes, "rain_timeline.png", "image/png"))
        if multiframe_bytes:
            media_items.append(ForecastMediaItem("photo", multiframe_bytes, "radar_multiframe.png", "image/png"))
        if hq_gif_bytes:
            media_items.append(ForecastMediaItem("document", hq_gif_bytes, "radar_nowcast_full.gif", "image/gif"))
        if gif_bytes:
            media_items.append(ForecastMediaItem("animation", gif_bytes, "radar_nowcast.gif", "image/gif"))
    elif cmd_name in ("/rain", "/check"):
        if tracking_bytes:
            media_items.append(ForecastMediaItem("photo", tracking_bytes, "radar_tracking.png", "image/png"))
        if gif_bytes:
            media_items.append(ForecastMediaItem("animation", gif_bytes, "radar_nowcast.gif", "image/gif"))
    elif cmd_name == "/radar":
        if static_bytes:
            media_items.append(ForecastMediaItem("photo", static_bytes, "radar_latest.png", "image/png"))
    elif cmd_name == "/tracking":
        if tracking_bytes:
            media_items.append(ForecastMediaItem("photo", tracking_bytes, "radar_tracking.png", "image/png"))
    elif cmd_name == "/timeline":
        if timeline_bytes:
            media_items.append(ForecastMediaItem("photo", timeline_bytes, "rain_timeline.png", "image/png"))
    elif cmd_name == "/nowcast":
        if gif_bytes:
            media_items.append(ForecastMediaItem("animation", gif_bytes, "radar_nowcast.gif", "image/gif"))

    return media_items


def build_formatted_forecast(
    result: dict,
    cmd_name: str = "/rain",
    show_advanced: bool = False,
    location_name: Optional[str] = None,
    advanced_data: Optional[dict] = None
) -> FormattedForecastResponse:
    """
    จัดรูปแบบผลลัพธ์พยากรณ์ฝนเป็น FormattedForecastResponse มาตรฐาน
    """
    text, actual_endpoint, eta_minutes = _build_forecast_text(result)

    if location_name:
        text = f"📍 **พื้นที่:** {location_name}\n\n" + text

    if result.get("is_outdated"):
        text = "⚠️ **ยังไม่มีข้อมูลล่าสุดจากกรมอุตุฯ (TMD Radar)**\nแนะนำให้เปลี่ยนไปใช้ API อื่น (เช่น Tomorrow.io หรือ Open-Meteo) แทนชั่วคราวครับ\n"

    adv_text = None
    if show_advanced or cmd_name == "/rain_pro":
        if advanced_data is not None:
            adv_text = _build_advanced_text(advanced_data)
        elif result.get("advanced_alerts"):
            adv_text = _build_advanced_text(result.get("advanced_alerts"))

    media_items = extract_forecast_media(
        result=result,
        cmd_name=cmd_name,
        show_advanced=show_advanced,
        location_name=location_name or "default"
    )

    return FormattedForecastResponse(
        text=text,
        actual_endpoint=actual_endpoint,
        eta_minutes=eta_minutes,
        advanced_text=adv_text,
        media_items=media_items
    )
