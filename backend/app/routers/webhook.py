from fastapi import APIRouter, Request, BackgroundTasks
import httpx
import os
import logging
from datetime import datetime
from app.services.rainbow import RainbowService
from app.services.location import get_location, save_location, delete_location
from app.database import async_sessionmaker, engine
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.telegram import send_telegram_message

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/webhook",
    tags=["webhook"]
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "mock_token")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
TELEGRAM_ANSWER_CB_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
TELEGRAM_EDIT_REPLY_MARKUP_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageReplyMarkup"

# AsyncSessionLocal for manual session management in background tasks
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

async def process_telegram_location(chat_id: int, lat: float, lng: float):
    try:
        rainbow = RainbowService()
        result = await rainbow.predict_rain_by_location(lat, lng)
        predictions = result.get("predictions", [])
        
        # Simple ETA logic
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
        
        if eta_minutes is not None:
            if eta_minutes == 0:
                text = "ฝนกำลังตกอยู่ที่พิกัดของคุณ ณ ขณะนี้\n"
            else:
                text = f"ฝนกำลังเคลื่อนมาทางทิศของคุณ จะตกหนักที่พิกัดของคุณในอีก {eta_minutes} นาที\n"
        else:
            text = "ยังไม่มีแนวโน้มฝนตกในบริเวณของคุณภายใน 1-2 ชั่วโมงนี้\n"
            
        # Check existing location
        has_existing_loc = False
        async with AsyncSessionLocal() as session:
            existing_loc = await get_location(session, chat_id)
            if existing_loc:
                has_existing_loc = True
                
        # Format inline keyboard data
        # Rounding to 4 decimals to keep callback_data small
        r_lat = round(lat, 4)
        r_lng = round(lng, 4)
        
        if has_existing_loc:
            text += "(คุณมีพิกัดเดิมบันทึกไว้อยู่แล้ว ต้องการอัปเดตเป็นพิกัดนี้ หรือลบของเดิมทิ้งหรือไม่?)"
            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": "🔄 อัปเดต (จำ 2 เดือน)", "callback_data": f"loc_2m_{r_lat}_{r_lng}"},
                        {"text": "🔄 อัปเดต (จำตลอดไป)", "callback_data": f"loc_inf_{r_lat}_{r_lng}"}
                    ],
                    [{"text": "🗑️ ลบพิกัดเดิม", "callback_data": "loc_del"}]
                ]
            }
        else:
            text += "(คุณต้องการให้ระบบจดจำตำแหน่งนี้สำหรับการแจ้งเตือนอัตโนมัติไหม?)"
            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": "⏳ จำ 2 เดือน", "callback_data": f"loc_2m_{r_lat}_{r_lng}"},
                        {"text": "♾️ จำตลอดไป", "callback_data": f"loc_inf_{r_lat}_{r_lng}"}
                    ],
                    [{"text": "❌ ไม่เป็นไร", "callback_data": "loc_no"}]
                ]
            }
            
        logger.info(f"Preparing to send message to chat_id={chat_id}: '{text}'")
        await send_telegram_message(chat_id, text, reply_markup)
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
    async with AsyncSessionLocal() as session:
        if data.startswith("loc_2m_") or data.startswith("loc_inf_"):
            parts = data.split("_")
            if len(parts) >= 4:
                try:
                    lat = float(parts[2])
                    lng = float(parts[3])
                    retention = "TWO_MONTHS" if data.startswith("loc_2m_") else "FOREVER"
                    await save_location(session, chat_id, lat, lng, retention)
                    answer_text = "บันทึกข้อมูลพิกัดเรียบร้อยแล้ว"
                except ValueError:
                    answer_text = "เกิดข้อผิดพลาดในการบันทึกพิกัด"
        elif data == "loc_del":
            await delete_location(session, chat_id)
            answer_text = "ลบข้อมูลพิกัดเดิมของคุณเรียบร้อยแล้ว"
        elif data == "loc_no":
            await delete_location(session, chat_id)
            answer_text = "ระบบรับทราบ จะไม่จดจำตำแหน่งของคุณ"
            
    async with httpx.AsyncClient() as client:
        # Answer Callback Query
        await client.post(TELEGRAM_ANSWER_CB_URL, json={
            "callback_query_id": query_id,
            "text": answer_text
        })
        # Remove Inline Keyboard
        if message_id:
            await client.post(TELEGRAM_EDIT_REPLY_MARKUP_URL, json={
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_markup": {"inline_keyboard": []}
            })

async def handle_mylocation_command(chat_id: int):
    async with AsyncSessionLocal() as session:
        loc = await get_location(session, chat_id)
        
    if not loc:
        text = "คุณยังไม่ได้บันทึกตำแหน่งใดๆ ไว้ในระบบ"
        reply_markup = None
    else:
        expires = "ไม่มีกำหนด (จำตลอดไป)"
        if loc.expires_at:
            expires = loc.expires_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        text = f"📍 พิกัดปัจจุบันของคุณ: {loc.latitude}, {loc.longitude}\n"
        text += f"⏳ วันหมดอายุ: {expires}\n\n"
        text += "หากต้องการเปลี่ยนแปลงพิกัด ให้ส่ง Location ใหม่อีกครั้ง หรือกดปุ่มด้านล่างเพื่อลบข้อมูลนี้"
        
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🗑️ ลบพิกัดเดิม", "callback_data": "loc_del"}]
            ]
        }
        
    await send_telegram_message(chat_id, text, reply_markup)

@router.post("/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    
    if "callback_query" in payload:
        background_tasks.add_task(handle_callback_query, payload["callback_query"])
        return {"status": "ok"}
    
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
                
        text = message.get("text", "")
        if text.startswith("/mylocation") and chat_id:
            background_tasks.add_task(handle_mylocation_command, chat_id)
            return {"status": "ok"}
                
    return {"status": "ignored"}
