import httpx
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "mock_token")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

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
