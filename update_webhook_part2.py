import re

with open("backend/app/routers/webhook.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Change button text
content = content.replace(
    '"text": "📊 เปรียบเทียบข้อมูล 4 API"',
    '"text": "📊 เปรียบเทียบข้อมูลจากทุกแหล่ง"'
)

# 2. Update signatures
content = content.replace(
    "async def handle_rain_command(chat_id: int, command: str, show_advanced: bool = False):",
    "async def handle_rain_command(chat_id: int, command: str, show_advanced: bool = False, message_id_to_edit: int = None):"
)
content = content.replace(
    "async def handle_devmock_command(chat_id: int, command: str, username: str = \"\"):",
    "async def handle_devmock_command(chat_id: int, command: str, username: str = \"\", message_id_to_edit: int = None):"
)
content = content.replace(
    "async def handle_metrics_command(chat_id: int, command: str, username: str = \"\"):",
    "async def handle_metrics_command(chat_id: int, command: str, username: str = \"\", message_id_to_edit: int = None):"
)
content = content.replace(
    "async def handle_setbudget_command(chat_id: int, command: str, username: str = \"\"):",
    "async def handle_setbudget_command(chat_id: int, command: str, username: str = \"\", message_id_to_edit: int = None):"
)
content = content.replace(
    "async def handle_tmd_fallback_command(chat_id: int, command: str, username: str = \"\"):",
    "async def handle_tmd_fallback_command(chat_id: int, command: str, username: str = \"\", message_id_to_edit: int = None):"
)

# 3. Update handle_rain_command body
old_rain_loading = """    msg_text = f"⏳ กำลังตรวจสอบสภาพอากาศที่ '{loc_display}' "
    if show_advanced:
        msg_text += "(โหมดผู้เชี่ยวชาญ)..."
    else:
        msg_text += "..."
        
    loading_msg_id = await send_telegram_message_return_id(chat_id, msg_text)"""

new_rain_loading = """    msg_text = f"⏳ กำลังตรวจสอบสภาพอากาศที่ '{loc_display}' "
    if show_advanced:
        msg_text += "(โหมดผู้เชี่ยวชาญ)..."
    else:
        msg_text += "..."
        
    if message_id_to_edit:
        await edit_telegram_message(chat_id, message_id_to_edit, msg_text)
        loading_msg_id = message_id_to_edit
    else:
        loading_msg_id = await send_telegram_message_return_id(chat_id, msg_text)"""
content = content.replace(old_rain_loading, new_rain_loading)

old_rain_all = """        if target_location_name == "all":
            await send_telegram_message(chat_id, f"⏳ กำลังตรวจสอบสภาพอากาศทั้งหมด {len(locs)} จุด...")"""

new_rain_all = """        if target_location_name == "all":
            if message_id_to_edit:
                await edit_telegram_message(chat_id, message_id_to_edit, f"⏳ กำลังตรวจสอบสภาพอากาศทั้งหมด {len(locs)} จุด...")
            else:
                await send_telegram_message(chat_id, f"⏳ กำลังตรวจสอบสภาพอากาศทั้งหมด {len(locs)} จุด...")"""
content = content.replace(old_rain_all, new_rain_all)


# 4. Update webhook caller blocks for rain commands
old_rain_calls = """        if text.startswith("/rain_pro") and chat_id:
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
            return {"status": "ok"}"""

new_rain_calls = """        if text.startswith("/rain_pro") and chat_id:
            loading_msg_id = await send_telegram_message_return_id(chat_id, "⏳ กำลังประมวลผล...")
            if not await tasks_svc.enqueue_task("worker/handle-rain", {"chat_id": chat_id, "command": text, "show_advanced": True, "message_id_to_edit": loading_msg_id}):
                background_tasks.add_task(handle_rain_command, chat_id, text, show_advanced=True, message_id_to_edit=loading_msg_id)
            return {"status": "ok"}

        if text.startswith("/rain") and chat_id:
            loading_msg_id = await send_telegram_message_return_id(chat_id, "⏳ กำลังประมวลผล...")
            if not await tasks_svc.enqueue_task("worker/handle-rain", {"chat_id": chat_id, "command": text, "message_id_to_edit": loading_msg_id}):
                background_tasks.add_task(handle_rain_command, chat_id, text, message_id_to_edit=loading_msg_id)
            return {"status": "ok"}

        if text.startswith("/devmock") and chat_id:
            loading_msg_id = await send_telegram_message_return_id(chat_id, "⏳ กำลังเข้าสู่ DevMock Mode...")
            if not await tasks_svc.enqueue_task("worker/handle-devmock", {"chat_id": chat_id, "command": text.strip(), "message_id_to_edit": loading_msg_id}):
                background_tasks.add_task(handle_devmock_command, chat_id, text.strip(), message_id_to_edit=loading_msg_id)
            return {"status": "ok"}"""
content = content.replace(old_rain_calls, new_rain_calls)


# 5. Update /check caller block
old_check_call = """        if text.strip() == "/check" and chat_id:
            logger.info(f"[WEBHOOK] /check received from chat_id={chat_id}, routing to handle_rain_command with 'tmd-radar'")
            if not await tasks_svc.enqueue_task("worker/handle-rain", {"chat_id": chat_id, "command": "/rain tmd-radar"}):
                background_tasks.add_task(handle_rain_command, chat_id, "/rain tmd-radar")
            return {"status": "ok"}"""

new_check_call = """        if text.strip() == "/check" and chat_id:
            logger.info(f"[WEBHOOK] /check received from chat_id={chat_id}, routing to handle_rain_command with 'tmd-radar'")
            loading_msg_id = await send_telegram_message_return_id(chat_id, "⏳ กำลังประมวลผล...")
            if not await tasks_svc.enqueue_task("worker/handle-rain", {"chat_id": chat_id, "command": "/rain tmd-radar", "message_id_to_edit": loading_msg_id}):
                background_tasks.add_task(handle_rain_command, chat_id, "/rain tmd-radar", message_id_to_edit=loading_msg_id)
            return {"status": "ok"}"""
content = content.replace(old_check_call, new_check_call)

# 6. Update caller block for admin commands
old_admin_calls = """        if text.startswith("/metrics") and chat_id:
            if not await tasks_svc.enqueue_task("worker/handle-metrics", {"chat_id": chat_id, "command": text.strip(), "username": username}):
                background_tasks.add_task(handle_metrics_command, chat_id, text.strip(), username)
            return {"status": "ok"}

        if text.startswith("/setbudget") and chat_id:
            if not await tasks_svc.enqueue_task("worker/handle-setbudget", {"chat_id": chat_id, "command": text.strip(), "username": username}):
                background_tasks.add_task(handle_setbudget_command, chat_id, text.strip(), username)
            return {"status": "ok"}"""

new_admin_calls = """        if text.startswith("/metrics") and chat_id:
            loading_msg_id = await send_telegram_message_return_id(chat_id, "⏳ กำลังดึงข้อมูลสถิติ...")
            if not await tasks_svc.enqueue_task("worker/handle-metrics", {"chat_id": chat_id, "command": text.strip(), "username": username, "message_id_to_edit": loading_msg_id}):
                background_tasks.add_task(handle_metrics_command, chat_id, text.strip(), username, message_id_to_edit=loading_msg_id)
            return {"status": "ok"}

        if text.startswith("/setbudget") and chat_id:
            loading_msg_id = await send_telegram_message_return_id(chat_id, "⏳ กำลังตั้งค่างบประมาณ...")
            if not await tasks_svc.enqueue_task("worker/handle-setbudget", {"chat_id": chat_id, "command": text.strip(), "username": username, "message_id_to_edit": loading_msg_id}):
                background_tasks.add_task(handle_setbudget_command, chat_id, text.strip(), username, message_id_to_edit=loading_msg_id)
            return {"status": "ok"}"""
content = content.replace(old_admin_calls, new_admin_calls)

old_tmd_fallback_call = """        if text.startswith("/tmd_fallback") and chat_id:
            if not await tasks_svc.enqueue_task("worker/handle-tmd-fallback", {"chat_id": chat_id, "command": text.strip(), "username": username}):
                background_tasks.add_task(handle_tmd_fallback_command, chat_id, text.strip(), username)
            return {"status": "ok"}"""

new_tmd_fallback_call = """        if text.startswith("/tmd_fallback") and chat_id:
            loading_msg_id = await send_telegram_message_return_id(chat_id, "⏳ กำลังสลับระบบข้อมูล...")
            if not await tasks_svc.enqueue_task("worker/handle-tmd-fallback", {"chat_id": chat_id, "command": text.strip(), "username": username, "message_id_to_edit": loading_msg_id}):
                background_tasks.add_task(handle_tmd_fallback_command, chat_id, text.strip(), username, message_id_to_edit=loading_msg_id)
            return {"status": "ok"}"""
content = content.replace(old_tmd_fallback_call, new_tmd_fallback_call)


with open("backend/app/routers/webhook.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated webhook.py (commands & check)")
