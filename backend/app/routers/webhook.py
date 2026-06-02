from fastapi import APIRouter, Request, BackgroundTasks
import httpx
import os
import logging
from datetime import datetime
from app.services.rainbow import RainbowService
from app.dependencies import get_repo_context
from app.services.telegram import send_telegram_message, edit_telegram_message, get_radar_inline_keyboard, send_telegram_document, DEVELOPER_CHAT_IDS
import json

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/telegram",
    tags=["webhook"]
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "mock_token")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
TELEGRAM_ANSWER_CB_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
TELEGRAM_EDIT_REPLY_MARKUP_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageReplyMarkup"


async def process_telegram_location(chat_id: int, lat: float, lng: float, endpoint_type: str = "global", message_id_to_edit: int = None):
    try:
        rainbow = RainbowService()
        result = await rainbow.predict_rain_by_location(lat, lng, endpoint_type=endpoint_type)
        predictions = result.get("predictions", [])
        actual_endpoint = result.get("endpoint", endpoint_type)
        
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
        
        endpoint_label = "Rainbow Global" if actual_endpoint == "global" else "Rainbow Local Radar"
        if eta_minutes is not None:
            intensity_str = result.get("intensity", "ไม่ทราบ")
            duration_min = result.get("duration_minutes", 0)
            
            if eta_minutes == 0:
                text = f"🌧️ ฝนกำลังตกอยู่ที่พิกัดของคุณ ณ ขณะนี้ (ตรวจสอบด้วย: {endpoint_label})\n"
            else:
                text = f"🌧️ ฝนกำลังเคลื่อนมาทางทิศของคุณ จะเริ่มตกในอีก {eta_minutes} นาที (ตรวจสอบด้วย: {endpoint_label})\n"
                
            text += f"💧 ความรุนแรง: {intensity_str}\n"
            text += f"⏱️ คาดว่าจะตกต่อเนื่องประมาณ: {duration_min} นาที\n"
        else:
            text = f"ยังไม่มีแนวโน้มฝนตกในบริเวณของคุณภายใน 1-2 ชั่วโมงนี้ (ตรวจสอบด้วย: {endpoint_label})\n"
            
        # Check existing location
        has_existing_loc = False
        async with get_repo_context() as repo:
            existing_loc = await repo.get_location(chat_id)
            if existing_loc:
                has_existing_loc = True
                
        # Format inline keyboard data
        # Rounding to 4 decimals to keep callback_data small
        r_lat = round(lat, 4)
        r_lng = round(lng, 4)
        
        keyboard = []
        
        if has_existing_loc:
            text += "(คุณมีพิกัดเดิมบันทึกไว้อยู่แล้ว ต้องการบันทึกพิกัดนี้เป็นอะไร หรือลบของเดิมทิ้ง?)"
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
            
        # Add Endpoint Switcher Buttons
        if actual_endpoint == "global":
            keyboard.append([{"text": "🔄 สลับไปใช้ Local Radar", "callback_data": f"switch_radar_{r_lat}_{r_lng}"}])
        else:
            keyboard.append([{"text": "🔄 สลับไปใช้ Global", "callback_data": f"switch_global_{r_lat}_{r_lng}"}])
            
        reply_markup = {"inline_keyboard": keyboard}
            
        logger.info(f"Preparing to send message to chat_id={chat_id}: '{text}'")
        
        if message_id_to_edit:
            await edit_telegram_message(chat_id, message_id_to_edit, text, reply_markup)
        else:
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
    async with get_repo_context() as repo:
        if data.startswith("loc_save_"):
            parts = data.split("_")
            # Format: loc_save_<name>_<retention>_<lat>_<lng>
            # Example: loc_save_Home_2m_13.1_100.1
            if len(parts) >= 6:
                try:
                    name = parts[2].lower() # e.g. "home", "work", "default"
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
            # For simplicity, if they click no, we don't do anything specific. 
            # If they had locations, we don't delete all of them.
            answer_text = "ระบบรับทราบ จะไม่จดจำตำแหน่งใหม่"
            
    # Handle Developer Raw Data Request
    if data.startswith("raw_"):
        if str(chat_id) not in DEVELOPER_CHAT_IDS:
            answer_text = "คุณไม่มีสิทธิ์เข้าถึงข้อมูลดิบ"
        else:
            parts = data.split("_")
            if len(parts) >= 3:
                try:
                    lat = float(parts[1])
                    lng = float(parts[2])
                    
                    # Fetch from Rainbow Service again
                    rainbow = RainbowService()
                    result = await rainbow.predict_rain_by_location(lat, lng)
                    
                    # Log to terminal
                    logger.info(f"Raw API Data for {lat}, {lng}: {json.dumps(result)}")
                    
                    # Send document
                    raw_bytes = json.dumps(result, indent=2).encode("utf-8")
                    await send_telegram_document(chat_id, raw_bytes, f"raw_{lat}_{lng}.json")
                    answer_text = "ส่งไฟล์ข้อมูลดิบเรียบร้อยแล้ว"
                except Exception as e:
                    logger.error(f"Error fetching raw data: {e}")
                    answer_text = "เกิดข้อผิดพลาดในการดึงข้อมูลดิบ"
            else:
                answer_text = "รูปแบบข้อมูลดิบไม่ถูกต้อง"
                
    # Handle Endpoint Switch
    if data.startswith("switch_radar_") or data.startswith("switch_global_"):
        parts = data.split("_")
        if len(parts) >= 4:
            try:
                lat = float(parts[2])
                lng = float(parts[3])
                endpoint_type = "radar" if data.startswith("switch_radar_") else "global"
                
                answer_text = "กำลังดึงข้อมูลใหม่..."
                
                # Await the process directly since we are already in a background task
                await process_telegram_location(chat_id, lat, lng, endpoint_type=endpoint_type, message_id_to_edit=message_id)
            except Exception as e:
                logger.error(f"Error handling switch endpoint: {e}")
                answer_text = "เกิดข้อผิดพลาดในการสลับแหล่งข้อมูล"

    async with httpx.AsyncClient() as client:
        # Answer Callback Query
        await client.post(TELEGRAM_ANSWER_CB_URL, json={
            "callback_query_id": query_id,
            "text": answer_text
        })
        # Remove Inline Keyboard (Only for location actions, skip for raw_data and switch)
        if message_id and not (data.startswith("raw_") or data.startswith("switch_")):
            await client.post(TELEGRAM_EDIT_REPLY_MARKUP_URL, json={
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_markup": {"inline_keyboard": []}
            })

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

@router.post("/webhook")
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
            
        if text.startswith("/radar") and chat_id:
            background_tasks.add_task(handle_radar_command, chat_id)
            return {"status": "ok"}
                
    return {"status": "ignored"}
