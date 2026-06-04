## Issue #38: Refactor Webhook → WeatherManager
- `[x]` ปรับ `WeatherManager.predict_rain()` รับ `force_endpoint` param
- `[x]` Refactor `process_telegram_location()` ใน webhook.py ให้ใช้ WeatherManager
- `[x]` Refactor `handle_callback_query` (raw data section) ให้ใช้ WeatherManager
- `[x]` ลบ import `RainbowService` ที่ไม่ใช้แล้วออกจาก webhook.py

## Issue #37: Loading State (Immediate Reply)
- `[x]` เพิ่ม `send_telegram_message_return_id()` ใน telegram.py
- `[x]` ส่งข้อความ "⏳ กำลังประมวลผล..." ทันทีในฟังก์ชัน `telegram_webhook` สำหรับ Location event
- `[x]` ส่ง `message_id` ต่อไปให้ background task เพื่อ edit ข้อความเมื่อเสร็จ
- `[x]` ทำเช่นเดียวกันสำหรับปุ่มสลับ endpoint (switch_radar/switch_global)

## Issue #26: Smart Cooldown (Severity Override)
- `[x]` เพิ่มคอลัมน์ `last_alert_max_rain` ใน models.py
- `[x]` ปรับ `update_last_alerted` signature ใน base.py
- `[x]` ปรับ `update_last_alerted` ใน sqlite.py ให้ save max_rain ด้วย
- `[x]` ปรับ `update_last_alerted` ใน firestore.py ให้ save max_rain ด้วย
- `[x]` สร้างสคริปต์ migration `scripts/migrate_issue26.py`
- `[x]` ปรับ `scheduler_tasks.py` ให้ทะลุ Cooldown หากความรุนแรงเพิ่มขึ้น
- `[x]` รัน migration script เพื่ออัปเดต schema จริง

## Verification
- `[x]` ตรวจสอบว่า tests ยังผ่าน (38/38 ✅)


## Issue #38: Refactor Webhook → WeatherManager
- `[ ]` ปรับ `WeatherManager.predict_rain()` รับ `force_endpoint` param
- `[ ]` Refactor `process_telegram_location()` ใน webhook.py ให้ใช้ WeatherManager
- `[ ]` Refactor `handle_callback_query` (raw data section) ให้ใช้ WeatherManager
- `[ ]` ลบ import `RainbowService` ที่ไม่ใช้แล้วออกจาก webhook.py

## Issue #37: Loading State (Immediate Reply)
- `[ ]` เพิ่ม `send_telegram_message_return_id()` ใน telegram.py
- `[ ]` ส่งข้อความ "⏳ กำลังประมวลผล..." ทันทีในฟังก์ชัน `telegram_webhook` สำหรับ Location event
- `[ ]` ส่ง `message_id` ต่อไปให้ background task เพื่อ edit ข้อความเมื่อเสร็จ
- `[ ]` ทำเช่นเดียวกันสำหรับปุ่มสลับ endpoint (switch_radar/switch_global)

## Issue #26: Smart Cooldown (Severity Override)
- `[ ]` เพิ่มคอลัมน์ `last_alert_max_rain` ใน models.py
- `[ ]` ปรับ `update_last_alerted` signature ใน base.py
- `[ ]` ปรับ `update_last_alerted` ใน sqlite.py ให้ save max_rain ด้วย
- `[ ]` ปรับ `update_last_alerted` ใน firestore.py ให้ save max_rain ด้วย
- `[ ]` สร้างสคริปต์ migration `scripts/migrate_issue26.py`
- `[ ]` ปรับ `scheduler_tasks.py` ให้ทะลุ Cooldown หากความรุนแรงเพิ่มขึ้น
- `[ ]` รัน migration script เพื่ออัปเดต schema จริง

## Verification
- `[ ]` ตรวจสอบว่า tests ยังผ่าน
