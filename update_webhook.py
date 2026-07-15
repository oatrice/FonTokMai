import re

with open("backend/app/routers/webhook.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update handle_callback_query signature
content = content.replace(
    "async def handle_callback_query(callback_query: dict):",
    "async def handle_callback_query(callback_query: dict, already_answered: bool = False):"
)

# 2. Update answer_callback_query calls in handle_callback_query
content = content.replace(
    "await answer_callback_query(query_id)\n            except ValueError:",
    "if not already_answered:\n                    await answer_callback_query(query_id)\n            except ValueError:"
)

content = content.replace(
    "await answer_callback_query(query_id)\n                \n            except Exception as e:",
    "if not already_answered:\n                    await answer_callback_query(query_id)\n                \n            except Exception as e:"
)

content = content.replace(
    "await answer_callback_query(query_id, text=answer_text)",
    "if not already_answered:\n        await answer_callback_query(query_id, text=answer_text)"
)

# 3. Update handle_lock_command signature
content = content.replace(
    "async def handle_lock_command(chat_id: int, command: str):",
    "async def handle_lock_command(chat_id: int, command: str, message_id_to_edit: int = None):"
)

# Replace returns in handle_lock_command
content = content.replace(
    """            if not locs:
                await send_telegram_message(chat_id, "⚠️ ไม่พบข้อมูลพิกัดหลักของคุณ กรุณาส่งพิกัดก่อนใช้งานคำสั่งนี้")
                return""",
    """            if not locs:
                if message_id_to_edit:
                    await edit_telegram_message(chat_id, message_id_to_edit, "⚠️ ไม่พบข้อมูลพิกัดหลักของคุณ กรุณาส่งพิกัดก่อนใช้งานคำสั่งนี้")
                else:
                    await send_telegram_message(chat_id, "⚠️ ไม่พบข้อมูลพิกัดหลักของคุณ กรุณาส่งพิกัดก่อนใช้งานคำสั่งนี้")
                return"""
)

content = content.replace(
    """                await send_telegram_message(
                    chat_id, 
                    "⚠️ รูปแบบคำสั่งไม่ถูกต้อง\\n"
                    "กรุณาใช้:\\n"
                    "- ล็อคช่องตาราง: `/lock [ชื่อพิกัด] D2` หรือ `/lock D2`\\n"
                    "- ล็อคพิกัดจริง: `/lock [ชื่อพิกัด] 13.75 100.5` หรือ `/lock 13.75 100.5`"
                )
                return""",
    """                error_msg = (
                    "⚠️ รูปแบบคำสั่งไม่ถูกต้อง\\n"
                    "กรุณาใช้:\\n"
                    "- ล็อคช่องตาราง: `/lock [ชื่อพิกัด] D2` หรือ `/lock D2`\\n"
                    "- ล็อคพิกัดจริง: `/lock [ชื่อพิกัด] 13.75 100.5` หรือ `/lock 13.75 100.5`"
                )
                if message_id_to_edit:
                    await edit_telegram_message(chat_id, message_id_to_edit, error_msg)
                else:
                    await send_telegram_message(chat_id, error_msg)
                return"""
)

content = content.replace(
    """                await send_telegram_message(
                    chat_id, 
                    "⚠️ รูปแบบตัวชี้เป้าไม่ถูกต้อง\\n"
                    "กรุณาใช้:\\n"
                    "- ล็อคกลุ่มฝน: `/lock [ชื่อพิกัด] A` หรือ `/lock A`\\n"
                    "- ล็อคช่องตาราง: `/lock [ชื่อพิกัด] D4`\\n"
                    "- ล็อคพิกัดจริง: `/lock [ชื่อพิกัด] 13.75 100.5`"
                )
                return""",
    """                error_msg = (
                    "⚠️ รูปแบบตัวชี้เป้าไม่ถูกต้อง\\n"
                    "กรุณาใช้:\\n"
                    "- ล็อคกลุ่มฝน: `/lock [ชื่อพิกัด] A` หรือ `/lock A`\\n"
                    "- ล็อคช่องตาราง: `/lock [ชื่อพิกัด] D4`\\n"
                    "- ล็อคพิกัดจริง: `/lock [ชื่อพิกัด] 13.75 100.5`"
                )
                if message_id_to_edit:
                    await edit_telegram_message(chat_id, message_id_to_edit, error_msg)
                else:
                    await send_telegram_message(chat_id, error_msg)
                return"""
)

content = content.replace(
    """        if processor is None or station_code is None:
            await send_telegram_message(chat_id, "⚠️ พิกัดหลักอยู่นอกขอบเขตของแผนที่เรดาร์")
            return""",
    """        if processor is None or station_code is None:
            if message_id_to_edit:
                await edit_telegram_message(chat_id, message_id_to_edit, "⚠️ พิกัดหลักอยู่นอกขอบเขตของแผนที่เรดาร์")
            else:
                await send_telegram_message(chat_id, "⚠️ พิกัดหลักอยู่นอกขอบเขตของแผนที่เรดาร์")
            return"""
)

content = content.replace(
    """                else:
                    await send_telegram_message(
                        chat_id,
                        f"⚠️ ไม่พบกลุ่มฝนป้ายกำกับ [{grid_lbl}] ในบริเวณรอบตัวคุณ หรือเมฆสลายตัวไปแล้ว"
                    )
                    return""",
    """                else:
                    error_msg = f"⚠️ ไม่พบกลุ่มฝนป้ายกำกับ [{grid_lbl}] ในบริเวณรอบตัวคุณ หรือเมฆสลายตัวไปแล้ว"
                    if message_id_to_edit:
                        await edit_telegram_message(chat_id, message_id_to_edit, error_msg)
                    else:
                        await send_telegram_message(chat_id, error_msg)
                    return"""
)

content = content.replace(
    """        if cx is None or cy is None or not (0 <= cx < frame_w and 0 <= cy < frame_h):
            await send_telegram_message(chat_id, "⚠️ พิกัดอยู่นอกขอบเขตของแผนที่เรดาร์")
            return""",
    """        if cx is None or cy is None or not (0 <= cx < frame_w and 0 <= cy < frame_h):
            if message_id_to_edit:
                await edit_telegram_message(chat_id, message_id_to_edit, "⚠️ พิกัดอยู่นอกขอบเขตของแผนที่เรดาร์")
            else:
                await send_telegram_message(chat_id, "⚠️ พิกัดอยู่นอกขอบเขตของแผนที่เรดาร์")
            return"""
)

content = content.replace(
    """        await send_telegram_message(chat_id, success_msg)
        await process_telegram_location(chat_id, lat, lng, location_name=loc_name, is_lock_command=True)
    except Exception as e:
        logger.error(f"Error handling lock command: {e}")
        await send_telegram_message(chat_id, f"❌ เกิดข้อผิดพลาด: {str(e)}")""",
    """        if message_id_to_edit:
            await edit_telegram_message(chat_id, message_id_to_edit, success_msg)
        else:
            await send_telegram_message(chat_id, success_msg)
        await process_telegram_location(chat_id, lat, lng, location_name=loc_name, is_lock_command=True)
    except Exception as e:
        logger.error(f"Error handling lock command: {e}")
        if message_id_to_edit:
            await edit_telegram_message(chat_id, message_id_to_edit, f"❌ เกิดข้อผิดพลาด: {str(e)}")
        else:
            await send_telegram_message(chat_id, f"❌ เกิดข้อผิดพลาด: {str(e)}")"""
)

# 4. Update handle_unlock_command
content = content.replace(
    "async def handle_unlock_command(chat_id: int, command: str):",
    "async def handle_unlock_command(chat_id: int, command: str, message_id_to_edit: int = None):"
)

content = content.replace(
    """            if not locs:
                await send_telegram_message(chat_id, "⚠️ ไม่พบข้อมูลพิกัดหลักของคุณ")
                return""",
    """            if not locs:
                if message_id_to_edit:
                    await edit_telegram_message(chat_id, message_id_to_edit, "⚠️ ไม่พบข้อมูลพิกัดหลักของคุณ")
                else:
                    await send_telegram_message(chat_id, "⚠️ ไม่พบข้อมูลพิกัดหลักของคุณ")
                return"""
)

content = content.replace(
    """        await send_telegram_message(chat_id, f"🔓 ปลดล็อคกลุ่มฝน (Auto-track) ของ {loc_name.capitalize()} เรียบร้อยแล้ว")
        await process_telegram_location(chat_id, lat, lng, location_name=loc_name, is_lock_command=True)
    except Exception as e:
        logger.error(f"Error handling unlock command: {e}")
        await send_telegram_message(chat_id, f"❌ เกิดข้อผิดพลาด: {str(e)}")""",
    """        success_msg = f"🔓 ปลดล็อคกลุ่มฝน (Auto-track) ของ {loc_name.capitalize()} เรียบร้อยแล้ว"
        if message_id_to_edit:
            await edit_telegram_message(chat_id, message_id_to_edit, success_msg)
        else:
            await send_telegram_message(chat_id, success_msg)
        await process_telegram_location(chat_id, lat, lng, location_name=loc_name, is_lock_command=True)
    except Exception as e:
        logger.error(f"Error handling unlock command: {e}")
        if message_id_to_edit:
            await edit_telegram_message(chat_id, message_id_to_edit, f"❌ เกิดข้อผิดพลาด: {str(e)}")
        else:
            await send_telegram_message(chat_id, f"❌ เกิดข้อผิดพลาด: {str(e)}")"""
)


# 5. Update _telegram_webhook_impl callback_query and commands

old_impl = """    if "callback_query" in payload:
        await handle_callback_query(payload["callback_query"])
        return {"status": "ok"}"""

new_impl = """    if "callback_query" in payload:
        callback_query = payload["callback_query"]
        query_id = callback_query.get("id")
        data = callback_query.get("data", "")
        
        is_heavy = data.startswith(("lock_target_", "unlock_target_", "switch_radar_", "switch_global_", "force_api_", "compare_api_", "raw_"))
        
        if is_heavy:
            from app.services.telegram import answer_callback_query
            toast_text = "กำลังประมวลผล..."
            if data.startswith("lock_target_"): toast_text = "กำลังล็อคเป้ากลุ่มฝน..."
            elif data.startswith("unlock_target_"): toast_text = "กำลังปลดล็อคกลุ่มฝน..."
            elif data.startswith("switch_"): toast_text = "กำลังดึงข้อมูลใหม่..."
            elif data.startswith("compare_api_"): toast_text = "กำลังดึงข้อมูลเปรียบเทียบ..."
            
            await answer_callback_query(query_id, text=toast_text)
            
            from app.services.cloud_tasks import CloudTasksService
            tasks_svc = CloudTasksService()
            if not await tasks_svc.enqueue_task("worker/handle-callback", {"callback_query": callback_query, "already_answered": True}):
                background_tasks.add_task(handle_callback_query, callback_query, already_answered=True)
            return {"status": "ok"}
        else:
            await handle_callback_query(callback_query)
            return {"status": "ok"}"""
content = content.replace(old_impl, new_impl)


old_lock = """        if text.startswith("/lock ") and chat_id:
            background_tasks.add_task(handle_lock_command, chat_id, text)
            return {"status": "ok"}
            
        if text.startswith("/unlock") and chat_id:
            background_tasks.add_task(handle_unlock_command, chat_id, text)
            return {"status": "ok"}"""

new_lock = """        if text.startswith("/lock ") and chat_id:
            loading_msg_id = await send_telegram_message_return_id(chat_id, "⏳ กำลังประมวลผล...")
            if not await tasks_svc.enqueue_task("worker/handle-lock", {"chat_id": chat_id, "command": text, "message_id_to_edit": loading_msg_id}):
                background_tasks.add_task(handle_lock_command, chat_id, text, loading_msg_id)
            return {"status": "ok"}
            
        if text.startswith("/unlock") and chat_id:
            loading_msg_id = await send_telegram_message_return_id(chat_id, "⏳ กำลังประมวลผล...")
            if not await tasks_svc.enqueue_task("worker/handle-unlock", {"chat_id": chat_id, "command": text, "message_id_to_edit": loading_msg_id}):
                background_tasks.add_task(handle_unlock_command, chat_id, text, loading_msg_id)
            return {"status": "ok"}"""
content = content.replace(old_lock, new_lock)


old_metrics = """        if text.startswith("/metrics") and chat_id:
            background_tasks.add_task(handle_metrics_command, chat_id, text.strip(), username)
            return {"status": "ok"}

        if text.startswith("/setbudget") and chat_id:
            background_tasks.add_task(handle_setbudget_command, chat_id, text.strip(), username)
            return {"status": "ok"}"""

new_metrics = """        if text.startswith("/metrics") and chat_id:
            if not await tasks_svc.enqueue_task("worker/handle-metrics", {"chat_id": chat_id, "command": text.strip(), "username": username}):
                background_tasks.add_task(handle_metrics_command, chat_id, text.strip(), username)
            return {"status": "ok"}

        if text.startswith("/setbudget") and chat_id:
            if not await tasks_svc.enqueue_task("worker/handle-setbudget", {"chat_id": chat_id, "command": text.strip(), "username": username}):
                background_tasks.add_task(handle_setbudget_command, chat_id, text.strip(), username)
            return {"status": "ok"}"""
content = content.replace(old_metrics, new_metrics)


old_fallback = """        if text.startswith("/tmd_fallback") and chat_id:
            background_tasks.add_task(handle_tmd_fallback_command, chat_id, text.strip(), username)
            return {"status": "ok"}"""

new_fallback = """        if text.startswith("/tmd_fallback") and chat_id:
            if not await tasks_svc.enqueue_task("worker/handle-tmd-fallback", {"chat_id": chat_id, "command": text.strip(), "username": username}):
                background_tasks.add_task(handle_tmd_fallback_command, chat_id, text.strip(), username)
            return {"status": "ok"}"""
content = content.replace(old_fallback, new_fallback)

with open("backend/app/routers/webhook.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated webhook.py")
