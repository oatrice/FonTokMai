# Walkthrough: Batch D — UX & Tech Debt

## สรุปสิ่งที่ทำ

### Issue #38 · Refactor Webhook → WeatherManager ✅

**ปัญหาเดิม:** `webhook.py` เรียก `RainbowService` โดยตรง (Hardcode) ทำให้ Webhook ไม่ผ่าน Fallback chain เหมือน Cron Job

**สิ่งที่เปลี่ยน:**

| ไฟล์ | การเปลี่ยนแปลง |
|---|---|
| `services/weather_manager.py` | เพิ่ม param `force_endpoint` เพื่อให้ผู้ใช้สลับ endpoint ได้โดยตรง โดยไม่กระทบ fallback chain ปกติ |
| `routers/webhook.py` | ลบ `import RainbowService` ออก → เรียก `WeatherManager().predict_rain()` แทนทุกที่ รวมถึง `raw_data` callback ด้วย |

ตอนนี้ทั้ง Webhook และ Cron Job ใช้ลอจิก fallback เดียวกัน:
```
Tomorrow.io → Rainbow Local → Rainbow Global
```

---

### Issue #37 · Immediate Reply / Loading State ✅

**ปัญหาเดิม:** ผู้ใช้ส่งพิกัดแล้วรอเงียบ 11-15 วินาที ไม่รู้ว่าบอทรับข้อมูลหรือยัง

**สิ่งที่เปลี่ยน:**

| ไฟล์ | การเปลี่ยนแปลง |
|---|---|
| `services/telegram.py` | เพิ่มฟังก์ชัน `send_telegram_message_return_id()` ที่ส่งข้อความแล้วคืน `message_id` |
| `routers/webhook.py` | เมื่อรับ Location event → ส่ง "⏳ กำลังประมวลผล..." ทันที แล้วส่ง `message_id` ต่อให้ background task เพื่อ `editMessageText` เมื่อผลลัพธ์พร้อม |

**Flow ใหม่:**
```
ผู้ใช้ส่ง Location
    ↓ (ทันที ~100ms)
Bot ส่ง "⏳ กำลังประมวลผลเรดาร์..."  ← ผู้ใช้เห็นทันที
    ↓ (background ~11-15s)
Bot แก้ไขข้อความเดิม → แสดงผลพยากรณ์จริง
```

---

### Issue #26 · Smart Cooldown (Severity Override) ✅

**ปัญหาเดิม:** ระบบ Cooldown 120 นาทีบล็อคการแจ้งเตือนทุกกรณี แม้แต่กรณีที่พายุทวีความรุนแรงขึ้น

**สิ่งที่เปลี่ยน:**

| ไฟล์ | การเปลี่ยนแปลง |
|---|---|
| `models.py` | เพิ่มคอลัมน์ `last_alert_max_rain FLOAT` ในตาราง `user_locations` |
| `repositories/base.py` | เพิ่ม param `max_rain` ใน `update_last_alerted()` |
| `repositories/sqlite.py` | บันทึก `max_rain` ลง DB เมื่อมีการแจ้งเตือน |
| `repositories/firestore.py` | บันทึก `max_rain` ลง Firestore เมื่อมีการแจ้งเตือน |
| `scheduler_tasks.py` | เพิ่มลอจิก Smart Cooldown: ถ้ายังติด cooldown แต่ `current_max_rain > last_alert_max_rain` → ทะลุบล็อก + เพิ่มส่วนหัว "⚠️ อัปเดต: ฝนทวีความรุนแรงขึ้น!" |
| `scripts/migrate_issue26.py` | สคริปต์ migration สำหรับเพิ่ม column ใหม่ (รันเรียบร้อยแล้ว) |

**Logic ใหม่:**
```python
if ติด_cooldown:
    current_rain = ดึงข้อมูลปัจจุบัน()
    if current_rain > last_alert_max_rain:
        # ทะลุบล็อก! แจ้งเตือนพร้อมข้อความพิเศษ
    else:
        continue  # ยังบล็อกอยู่
```

---

## ผลการทดสอบ

```
38 passed in 2.19s ✅
```

| Test ใหม่/แก้ | ผล |
|---|---|
| `test_telegram_webhook_with_location` | ✅ (refactored to use WeatherManager + loading state) |
| `test_telegram_webhook_without_location` | ✅ (refactored to use WeatherManager) |
| `test_check_rain_and_alert_recently_alerted` | ✅ (updated: last_alert_max_rain=same → no override) |
| `test_check_rain_and_alert_smart_cooldown_override` | ✅ (NEW: rain 2.0→8.0 mm/hr → triggers override) |
