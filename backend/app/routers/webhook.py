from fastapi import APIRouter, Request, BackgroundTasks
import httpx
import os
import logging
from app.services.rainbow import RainbowService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/webhook",
    tags=["webhook"]
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "mock_token")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

from datetime import datetime

async def process_telegram_location(chat_id: int, lat: float, lng: float):
    try:
        rainbow = RainbowService()
        result = await rainbow.predict_rain_by_location(lat, lng)
        predictions = result.get("predictions", [])
        
        # Simple ETA logic
        eta_minutes = None
        if predictions:
            try:
                # support Python 3.9 where Z is not parsed by fromisoformat
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
        
        if eta_minutes is not None:
            if eta_minutes == 0:
                text = "ฝนกำลังตกอยู่ที่พิกัดของคุณ ณ ขณะนี้"
            else:
                text = f"ฝนกำลังเคลื่อนมาทางทิศของคุณ จะตกหนักที่พิกัดของคุณในอีก {eta_minutes} นาที"
        else:
            text = "ยังไม่มีแนวโน้มฝนตกในบริเวณของคุณภายใน 1-2 ชั่วโมงนี้"
            
        logger.info(f"Preparing to send message to chat_id={chat_id}: '{text}'")
        async with httpx.AsyncClient() as client:
            response = await client.post(TELEGRAM_API_URL, json={
                "chat_id": chat_id,
                "text": text
            })
            if response.status_code != 200:
                logger.warning(f"Telegram API responded with {response.status_code}: {response.text}")
            else:
                logger.info(f"Successfully sent message to chat_id={chat_id}")
    except Exception as e:
        logger.error(f"Error processing telegram location: {e}")
        try:
            async with httpx.AsyncClient() as client:
                await client.post(TELEGRAM_API_URL, json={
                    "chat_id": chat_id,
                    "text": "ขออภัย ไม่สามารถดึงข้อมูลพยากรณ์ฝนได้ในขณะนี้"
                })
        except Exception as inner_e:
            logger.error(f"Failed to send fallback error message: {inner_e}")

@router.post("/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    
    if "message" in payload:
        message = payload["message"]
        chat_id = message.get("chat", {}).get("id")
        
        if "location" in message and chat_id:
            location = message["location"]
            lat = location.get("latitude")
            lng = location.get("longitude")
            
            if lat and lng:
                background_tasks.add_task(process_telegram_location, chat_id, lat, lng)
                return {"status": "ok"}
                
    return {"status": "ignored"}
