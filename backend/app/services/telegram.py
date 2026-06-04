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
TELEGRAM_SEND_DOC_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
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
        async with httpx.AsyncClient() as client:
            response = await client.post(TELEGRAM_EDIT_MESSAGE_URL, json=payload)
            if response.status_code != 200:
                logger.warning(f"Telegram API responded with {response.status_code}: {response.text}")
                return False
            return True
    except Exception as e:
        logger.error(f"Failed to edit telegram message {message_id} in {chat_id}: {e}")
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
        async with httpx.AsyncClient() as client:
            response = await client.post(TELEGRAM_API_URL, json=payload)
            if response.status_code != 200:
                logger.warning(f"Telegram API responded with {response.status_code}: {response.text}")
                return False
            return True
    except Exception as e:
        logger.error(f"Failed to send telegram message to {chat_id}: {e}")
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
        async with httpx.AsyncClient() as client:
            response = await client.post(TELEGRAM_API_URL, json=payload)
            if response.status_code != 200:
                logger.warning(f"Telegram API responded with {response.status_code}: {response.text}")
                return None
            data = response.json()
            return data.get("result", {}).get("message_id")
    except Exception as e:
        logger.error(f"Failed to send telegram loading message to {chat_id}: {e}")
        return None



async def send_telegram_document(chat_id: int, file_data: bytes, filename: str) -> bool:
    """
    Sends a document to a specific Telegram chat_id.
    """
    try:
        async with httpx.AsyncClient() as client:
            files = {"document": (filename, file_data, "application/json")}
            data = {"chat_id": chat_id}
            response = await client.post(TELEGRAM_SEND_DOC_URL, data=data, files=files)
            if response.status_code != 200:
                logger.warning(f"Telegram API responded with {response.status_code}: {response.text}")
                return False
            return True
    except Exception as e:
        logger.error(f"Failed to send telegram document to {chat_id}: {e}")
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
