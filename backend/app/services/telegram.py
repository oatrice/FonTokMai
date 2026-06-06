import httpx
import os
import logging
import json
import io
from typing import Optional

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "mock_token")
DEVELOPER_CHAT_IDS = os.getenv("DEVELOPER_CHAT_IDS", "").split(",")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
TELEGRAM_SEND_ANIMATION_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAnimation"
TELEGRAM_SEND_DOC_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
TELEGRAM_SEND_PHOTO_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
TELEGRAM_EDIT_MESSAGE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"

async def edit_telegram_message(chat_id: int, message_id: int, text: str, reply_markup: Optional[dict] = None) -> bool:
    """
    Edits a previously sent message in a specific Telegram chat_id.
    """
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
        
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(TELEGRAM_EDIT_MESSAGE_URL, json=payload)
            if response.status_code != 200:
                logger.warning(f"Telegram API responded with {response.status_code}: {response.text}")
                return False
            return True
    except Exception as e:
        logger.error(f"Failed to edit telegram message {message_id} in {chat_id}: {type(e).__name__} - {e}")
        return False
async def send_telegram_message(chat_id: int, text: str, reply_markup: Optional[dict] = None) -> bool:
    """
    Sends a message to a specific Telegram chat_id.
    """
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
        
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(TELEGRAM_API_URL, json=payload)
            if response.status_code != 200:
                logger.warning(f"Telegram API responded with {response.status_code}: {response.text}")
                return False
            return True
    except Exception as e:
        logger.error(f"Failed to send telegram message to {chat_id}: {type(e).__name__} - {e}")
        return False

async def send_telegram_message_return_id(chat_id: int, text: str) -> Optional[int]:
    """
    Sends a message to a specific Telegram chat_id and returns the message_id.
    Used for sending immediate "loading..." messages that will be edited later.
    Returns None on failure.
    """
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(TELEGRAM_API_URL, json=payload)
            if response.status_code != 200:
                logger.warning(f"Telegram API responded with {response.status_code}: {response.text}")
                return None
            data = response.json()
            return data.get("result", {}).get("message_id")
    except Exception as e:
        logger.error(f"Failed to send telegram loading message to {chat_id}: {type(e).__name__} - {e}")
        return None



async def send_telegram_document(chat_id: int, file_data: bytes, filename: str) -> bool:
    """
    Sends a document/animation to a specific Telegram chat_id.
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {"animation": (filename, file_data, "image/gif")}
            data = {"chat_id": chat_id}
            response = await client.post(TELEGRAM_SEND_ANIMATION_URL, data=data, files=files)
            if response.status_code != 200:
                logger.warning(f"Telegram API responded with {response.status_code}: {response.text}")
                return False
            return True
    except Exception as e:
        logger.error(f"Failed to send telegram animation to {chat_id}: {e}")
        return False

async def send_telegram_raw_document(chat_id: int, file_data: bytes, filename: str) -> bool:
    """
    Sends a file as an uncompressed document to a specific Telegram chat_id.
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {"document": (filename, file_data, "image/gif")}
            data = {"chat_id": chat_id}
            response = await client.post(TELEGRAM_SEND_DOC_URL, data=data, files=files)
            if response.status_code != 200:
                logger.warning(f"Telegram API responded with {response.status_code}: {response.text}")
                return False
            return True
    except Exception as e:
        logger.error(f"Failed to send telegram raw document to {chat_id}: {e}")
        return False

async def send_telegram_photo(chat_id: int, photo_data: bytes, filename: str) -> bool:
    """
    Sends a photo to a specific Telegram chat_id.
    """
    try:
        async with httpx.AsyncClient() as client:
            files = {"photo": (filename, photo_data, "image/png")}
            data = {"chat_id": chat_id}
            response = await client.post(TELEGRAM_SEND_PHOTO_URL, data=data, files=files)
            if response.status_code != 200:
                logger.warning(f"Telegram API responded with {response.status_code}: {response.text}")
                return False
            return True
    except Exception as e:
        logger.error(f"Failed to send telegram photo to {chat_id}: {e}")
        return False

def get_radar_inline_keyboard(lat: float, lng: float, is_developer: bool = False) -> dict:
    """Returns a Telegram inline keyboard markup with multi-source radar links."""
    keyboard = [
        [{"text": "📡 Zoom Earth", "url": f"https://zoom.earth/maps/radar/#view={lat},{lng},10z"}],
        [{"text": "🌪️ Windy Radar", "url": f"https://www.windy.com/-Weather-radar-radar?radar,{lat},{lng},10"}],
        [{"text": "🇹🇭 TMD Radar", "url": "https://weather.tmd.go.th/"}]
    ]
    
    if is_developer:
        keyboard.append([{"text": "📊 ดูข้อมูลดิบ", "callback_data": f"raw_{lat:.4f}_{lng:.4f}"}])
        
    return {
        "inline_keyboard": keyboard
    }

async def send_grouped_disaster_alert(chat_id: int, event_type: str, event_data: dict, locations_info: list) -> bool:
    """Send proactive disaster alert for multiple locations belonging to the same user."""
    
    locations_text = "\n".join([f"📍 <b>{loc.name}:</b> ห่าง {dist:.1f} กม." for loc, dist in locations_info])
    
    if event_type == "earthquake":
        mag = event_data.get("mag", 0)
        place = event_data.get("place", "Unknown Location")
        text = (
            f"🚨 <b>ด่วน! แจ้งเตือนแผ่นดินไหว</b>\n\n"
            f"📍 <b>จุดเกิดเหตุ:</b> {place}\n"
            f"⚠️ <b>ขนาด:</b> {mag} ริกเตอร์\n\n"
            f"<b>พิกัดของคุณที่ได้รับผลกระทบ:</b>\n"
            f"{locations_text}\n\n"
            f"โปรดระมัดระวังและติดตามข่าวสารอย่างใกล้ชิด"
        )
    elif event_type == "cyclone":
        name = event_data.get("name", "Unknown")
        cat = event_data.get("category", "")
        text = (
            f"🌀 <b>แจ้งเตือนพายุหมุนเขตร้อน</b>\n\n"
            f"🌪️ <b>ชื่อพายุ:</b> {name} ({cat})\n\n"
            f"<b>พิกัดของคุณที่ได้รับผลกระทบ:</b>\n"
            f"{locations_text}\n\n"
            f"โปรดเตรียมรับมือฝนตกหนักและลมกระโชกแรง"
        )
    elif event_type == "fire":
        name = event_data.get("name", "Wildfire")
        text = (
            f"🔥 <b>แจ้งเตือนไฟป่า/จุดความร้อน</b>\n\n"
            f"📍 <b>บริเวณ:</b> {name}\n\n"
            f"<b>พิกัดของคุณที่ได้รับผลกระทบ:</b>\n"
            f"{locations_text}\n\n"
            f"โปรดระวังกลุ่มควันและค่าฝุ่นละออง (PM2.5) ที่อาจพัดผ่าน"
        )
    else:
        text = f"⚠️ <b>แจ้งเตือนภัยพิบัติ</b>\nเกิดเหตุ {event_type}\n<b>พิกัดที่กระทบ:</b>\n{locations_text}"

    # Parse mode HTML is supported by default telegram.py wrapper if we use normal text?
    # Wait, send_telegram_message doesn't have parse_mode="HTML" parameter in the payload.
    # Let's add it.
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(TELEGRAM_API_URL, json=payload)
            if response.status_code != 200:
                logger.warning(f"Telegram API responded with {response.status_code}: {response.text}")
                return False
            return True
    except Exception as e:
        logger.error(f"Failed to send disaster alert to {chat_id}: {e}")
        return False
