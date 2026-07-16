from fastapi import APIRouter, Request, BackgroundTasks
import logging
from datetime import datetime, timezone
from app.services import telegram
from app.services.command_router import router as cmd_router
from app.routers.webhook_utils import (
    LAST_ACTIVE_LOCATION, LAST_PINNED_LOCATION,
    check_admin_access
)

router = APIRouter(
    prefix="/api/v1/telegram",
    tags=["webhook"]
)

logger = logging.getLogger(__name__)

from app.routers.webhook_callbacks import handle_callback_query
from app.routers.webhook_location import process_telegram_location
from app.routers import webhook_commands, webhook_admin, webhook_devmock




















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
            await telegram.send_telegram_message(chat_id, "⚠️ ระบบยุ่งชั่วคราว กรุณาลองใหม่อีกครั้ง")
        return {"status": "error", "detail": str(e)}















async def _telegram_webhook_impl(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()

    if "callback_query" in payload:
        callback_query = payload["callback_query"]
        query_id = callback_query.get("id")
        data = callback_query.get("data", "")
        
        is_heavy = data.startswith(("lock_target_", "unlock_target_", "switch_radar_", "switch_global_", "force_api_", "compare_api_", "raw_"))
        
        if is_heavy:
            toast_text = "กำลังประมวลผล..."
            if data.startswith("lock_target_"): toast_text = "กำลังล็อคเป้ากลุ่มฝน..."
            elif data.startswith("unlock_target_"): toast_text = "กำลังปลดล็อคกลุ่มฝน..."
            elif data.startswith("switch_"): toast_text = "กำลังดึงข้อมูลใหม่..."
            elif data.startswith("compare_api_"): toast_text = "กำลังดึงข้อมูลเปรียบเทียบ..."
            
            await telegram.answer_callback_query(query_id, text=toast_text)
            
            from app.services.cloud_tasks import CloudTasksService
            tasks_svc = CloudTasksService()
            if not await tasks_svc.enqueue_task("worker/handle-callback", {"callback_query": callback_query, "already_answered": True}):
                background_tasks.add_task(handle_callback_query, callback_query, already_answered=True)
            return {"status": "ok"}
        else:
            await handle_callback_query(callback_query)
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
                loading_msg_id = await telegram.send_telegram_message_return_id(
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

        # Dispatch command via ZCode-inspired Command Router
        handled = await cmd_router.dispatch(
            text=text,
            chat_id=chat_id,
            username=username,
            background_tasks=background_tasks,
            check_admin_access_fn=check_admin_access,
            send_telegram_message_fn=telegram.send_telegram_message,
            send_telegram_message_return_id_fn=telegram.send_telegram_message_return_id,
            enqueue_task_fn=tasks_svc.enqueue_task,
        )
        if handled:
            return {"status": "ok"}



        logger.debug(f"[WEBHOOK] Unrecognized command or text, returning ignored. text='{text}'")

    return {"status": "ignored"}
