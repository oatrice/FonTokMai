import re

with open("backend/app/routers/webhook.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace send_telegram_message with edit if message_id_to_edit is provided, inside the relevant commands.

def patch_send(cmd_body):
    # This is a bit tricky, let's just replace `await send_telegram_message(chat_id, ` with a conditional block
    # We will use regex to find await send_telegram_message(chat_id, <text>)
    # But it's easier to just do it manually for the known lines.
    pass

# For devmock
content = content.replace(
    """await send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: 🌧️ ฝนตกหนัก (Boost เมฆจริง)\\n⏳ กำลังสร้างแจ้งเตือน...")""",
    """if message_id_to_edit: await edit_telegram_message(chat_id, message_id_to_edit, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: 🌧️ ฝนตกหนัก (Boost เมฆจริง)\\n⏳ กำลังสร้างแจ้งเตือน...")\n            else: await send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: 🌧️ ฝนตกหนัก (Boost เมฆจริง)\\n⏳ กำลังสร้างแจ้งเตือน...")"""
)
content = content.replace(
    """await send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: 🌪️ พายุจำลอง (สร้างเมฆปลอม 5 สี)\\n⏳ กำลังสร้างแจ้งเตือน...")""",
    """if message_id_to_edit: await edit_telegram_message(chat_id, message_id_to_edit, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: 🌪️ พายุจำลอง (สร้างเมฆปลอม 5 สี)\\n⏳ กำลังสร้างแจ้งเตือน...")\n            else: await send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: 🌪️ พายุจำลอง (สร้างเมฆปลอม 5 สี)\\n⏳ กำลังสร้างแจ้งเตือน...")"""
)
content = content.replace(
    """await send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: ☀️ ท้องฟ้าแจ่มใส\\n⏳ กำลังตรวจสอบสภาพอากาศ...")""",
    """if message_id_to_edit: await edit_telegram_message(chat_id, message_id_to_edit, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: ☀️ ท้องฟ้าแจ่มใส\\n⏳ กำลังตรวจสอบสภาพอากาศ...")\n            else: await send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: ☀️ ท้องฟ้าแจ่มใส\\n⏳ กำลังตรวจสอบสภาพอากาศ...")"""
)
content = content.replace(
    """await send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: ❌ เชื่อมต่อ API ล้มเหลวทั้งหมด\\n⏳ กำลังส่งตำแหน่งเพื่อทดสอบ Fallback...")""",
    """if message_id_to_edit: await edit_telegram_message(chat_id, message_id_to_edit, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: ❌ เชื่อมต่อ API ล้มเหลวทั้งหมด\\n⏳ กำลังส่งตำแหน่งเพื่อทดสอบ Fallback...")\n            else: await send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: ❌ เชื่อมต่อ API ล้มเหลวทั้งหมด\\n⏳ กำลังส่งตำแหน่งเพื่อทดสอบ Fallback...")"""
)
content = content.replace(
    """await send_telegram_message(chat_id, "ไม่พบตำแหน่งที่บันทึกไว้ โปรดส่ง Location มาใหม่เพื่อทดสอบ error")""",
    """if message_id_to_edit: await edit_telegram_message(chat_id, message_id_to_edit, "ไม่พบตำแหน่งที่บันทึกไว้ โปรดส่ง Location มาใหม่เพื่อทดสอบ error")\n                else: await send_telegram_message(chat_id, "ไม่พบตำแหน่งที่บันทึกไว้ โปรดส่ง Location มาใหม่เพื่อทดสอบ error")"""
)

# For metrics
content = content.replace(
    """await send_telegram_message(chat_id, f"📊 สถิติระบบ (Server: {os.getenv('ENVIRONMENT', 'unknown')})\\n"
                                             f"====================\\n"
                                             f"{cache_stats_str}\\n"
                                             f"{active_tasks}\\n"
                                             f"{worker_stats}")""",
    """if message_id_to_edit: await edit_telegram_message(chat_id, message_id_to_edit, f"📊 สถิติระบบ (Server: {os.getenv('ENVIRONMENT', 'unknown')})\\n====================\\n{cache_stats_str}\\n{active_tasks}\\n{worker_stats}")\n        else: await send_telegram_message(chat_id, f"📊 สถิติระบบ (Server: {os.getenv('ENVIRONMENT', 'unknown')})\\n====================\\n{cache_stats_str}\\n{active_tasks}\\n{worker_stats}")"""
)

# For setbudget
content = content.replace(
    """await send_telegram_message(chat_id, "⚠️ กรุณาระบุจำนวนที่ต้องการตั้งค่า เช่น `/setbudget 500`")""",
    """if message_id_to_edit: await edit_telegram_message(chat_id, message_id_to_edit, "⚠️ กรุณาระบุจำนวนที่ต้องการตั้งค่า เช่น `/setbudget 500`")\n        else: await send_telegram_message(chat_id, "⚠️ กรุณาระบุจำนวนที่ต้องการตั้งค่า เช่น `/setbudget 500`")"""
)
content = content.replace(
    """await send_telegram_message(chat_id, "⚠️ ค่าที่ระบุต้องเป็นตัวเลข เช่น `/setbudget 500`")""",
    """if message_id_to_edit: await edit_telegram_message(chat_id, message_id_to_edit, "⚠️ ค่าที่ระบุต้องเป็นตัวเลข เช่น `/setbudget 500`")\n        else: await send_telegram_message(chat_id, "⚠️ ค่าที่ระบุต้องเป็นตัวเลข เช่น `/setbudget 500`")"""
)
content = content.replace(
    """await send_telegram_message(chat_id, f"✅ อัปเดต Monthly Budget เป็น ${new_budget} เรียบร้อยแล้ว")""",
    """if message_id_to_edit: await edit_telegram_message(chat_id, message_id_to_edit, f"✅ อัปเดต Monthly Budget เป็น ${new_budget} เรียบร้อยแล้ว")\n        else: await send_telegram_message(chat_id, f"✅ อัปเดต Monthly Budget เป็น ${new_budget} เรียบร้อยแล้ว")"""
)
content = content.replace(
    """await send_telegram_message(chat_id, f"❌ เกิดข้อผิดพลาด: {str(e)}")""",
    """if message_id_to_edit: await edit_telegram_message(chat_id, message_id_to_edit, f"❌ เกิดข้อผิดพลาด: {str(e)}")\n        else: await send_telegram_message(chat_id, f"❌ เกิดข้อผิดพลาด: {str(e)}")"""
)

# For tmd_fallback
content = content.replace(
    """await send_telegram_message(chat_id, "⚠️ ระบบนี้สงวนไว้สำหรับผู้ดูแลระบบเท่านั้น")""",
    """if message_id_to_edit: await edit_telegram_message(chat_id, message_id_to_edit, "⚠️ ระบบนี้สงวนไว้สำหรับผู้ดูแลระบบเท่านั้น")\n        else: await send_telegram_message(chat_id, "⚠️ ระบบนี้สงวนไว้สำหรับผู้ดูแลระบบเท่านั้น")"""
)
content = content.replace(
    """await send_telegram_message(chat_id, "✅ ระบบกำลังใช้ API ปกติ (Open-Meteo) เป็นหลัก")""",
    """if message_id_to_edit: await edit_telegram_message(chat_id, message_id_to_edit, "✅ ระบบกำลังใช้ API ปกติ (Open-Meteo) เป็นหลัก")\n        else: await send_telegram_message(chat_id, "✅ ระบบกำลังใช้ API ปกติ (Open-Meteo) เป็นหลัก")"""
)
content = content.replace(
    """await send_telegram_message(chat_id, "✅ ระบบเปิดใช้งาน TMD Fallback Mode แล้ว (ใช้ TMD เป็นหลักชั่วคราว)")""",
    """if message_id_to_edit: await edit_telegram_message(chat_id, message_id_to_edit, "✅ ระบบเปิดใช้งาน TMD Fallback Mode แล้ว (ใช้ TMD เป็นหลักชั่วคราว)")\n        else: await send_telegram_message(chat_id, "✅ ระบบเปิดใช้งาน TMD Fallback Mode แล้ว (ใช้ TMD เป็นหลักชั่วคราว)")"""
)

with open("backend/app/routers/webhook.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated send_telegram_message calls")
