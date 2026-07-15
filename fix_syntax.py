import re
with open("backend/app/routers/webhook.py", "r", encoding="utf-8") as f:
    content = f.read()

bad_str = """        else:
            if message_id_to_edit: await edit_telegram_message(chat_id, message_id_to_edit, f"❌ เกิดข้อผิดพลาด: {str(e)}")
        else: await send_telegram_message(chat_id, f"❌ เกิดข้อผิดพลาด: {str(e)}")"""

good_str = """        else:
            await send_telegram_message(chat_id, f"❌ เกิดข้อผิดพลาด: {str(e)}")"""

content = content.replace(bad_str, good_str)

with open("backend/app/routers/webhook.py", "w", encoding="utf-8") as f:
    f.write(content)
