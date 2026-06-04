# แผนการทำงาน Batch D (UX & Tech Debt)

แผนนี้ครอบคลุม 3 งานหลัก ได้แก่ การแก้ไข Tech Debt ของ Webhook (Issue #38), การเพิ่ม Loading State ระหว่างประมวลผล (Issue #37) และการทำ Smart Cooldown (Issue #26)

## Proposed Changes

### Issue #38: Refactor Webhook to use WeatherManager (ด่วนที่สุด)

- **`backend/app/services/weather_manager.py`**
  - **[MODIFY]** ปรับแก้ `predict_rain` ให้รับพารามิเตอร์ `force_endpoint: Optional[str] = None` เพิ่มเติม
  - ถ้ามี `force_endpoint` ระบุมา (เช่น `"global"` หรือ `"local"`) ให้เรียกบริการที่กำหนดโดยไม่ต้องทำ fallback

- **`backend/app/routers/webhook.py`**
  - **[MODIFY]** เปลี่ยนการเรียกใช้ `RainbowService().predict_rain_by_location(...)` ใน `process_telegram_location` เป็น `WeatherManager().predict_rain(...)` โดยส่ง `force_endpoint` ตามความเหมาะสม
  - คงรูปแบบข้อความการทำงานเดิมไว้

---

### Issue #37: Immediate Reply / Loading State

- **`backend/app/services/telegram.py`**
  - **[MODIFY]** สร้างฟังก์ชันใหม่ `send_telegram_message_return_id(chat_id: int, text: str) -> Optional[int]` เพื่อใช้ส่งข้อความและดึงเอา `message_id` กลับมา (ใช้สำหรับข้อความโหลดที่ส่งกลับทันที)

- **`backend/app/routers/webhook.py`**
  - **[MODIFY]** ในฟังก์ชัน `telegram_webhook` เมื่อรับ Event ส่งพิกัดใหม่ หรือเมื่อมีการสลับแหล่งข้อมูล ให้รอส่งข้อความ "⏳ กำลังประมวลผลเรดาร์และพยากรณ์อากาศ..." กลับไปให้ผู้ใช้ทันทีก่อนที่จะสั่งงานให้ Background Task ไปประมวลผล และส่ง `message_id` ของข้อความนี้ไปที่พารามิเตอร์ `message_id_to_edit` ในฟังก์ชัน `process_telegram_location` เพื่อแก้ไข (edit) ข้อความนั้นเมื่อประมวลผลเสร็จแล้ว

---

### Issue #26: Smart Cooldown (Severity Override)

- **`backend/app/models.py`**
  - **[MODIFY]** เพิ่มคอลัมน์ `last_alert_max_rain = Column(Float, nullable=True, default=0.0)` ให้คลาส `UserLocation` เพื่อเก็บค่าปริมาณฝนที่แจ้งเตือนครั้งล่าสุด

- **`backend/app/repositories/base.py`**
  - **[MODIFY]** เพิ่มพารามิเตอร์ `max_rain: Optional[float] = None` ให้ฟังก์ชัน `update_last_alerted`

- **`backend/app/repositories/sqlite.py`** และ **`backend/app/repositories/firestore.py`**
  - **[MODIFY]** ปรับ `update_last_alerted` ให้รองรับการอัปเดตค่าความรุนแรงของฝน (max_rain) ที่แจ้งเตือนครั้งล่าสุดลงในฐานข้อมูล

- **`backend/scripts/migrate_issue26.py`**
  - **[NEW]** สร้างสคริปต์สั้น ๆ ใช้ SQLAlchemy + Sqlite รัน `ALTER TABLE user_locations ADD COLUMN last_alert_max_rain FLOAT DEFAULT 0.0;` ในฐานข้อมูล

- **`backend/app/scheduler_tasks.py`**
  - **[MODIFY]** ใน `check_rain_and_alert` ก่อนข้ามลูป (continue) หากติด Cooldown อยู่ ให้ตรวจสอบว่า:
    - ถ้าค่า `max_rain` ปัจจุบัน **มากกว่า** ค่า `loc.last_alert_max_rain` (เช่น รอบก่อนแจ้ง 2.0 mm/hr แต่มารอบนี้เจอพายุเข้าเป็น 10.0 mm/hr) 
    - ระบบจะทำการแจ้งเตือนแบบข้าม Cooldown ได้ทันที พร้อมลบเครื่องหมาย "ทะลุบล็อก" เช่น "⚠️ **อัปเดต: พายุทวีความรุนแรงขึ้น!**"

## Verification Plan

### Automated Tests / Manual Verification
1. สั่งรันสคริปต์ migration `scripts/migrate_issue26.py` และตรวจสอบว่าทำงานสำเร็จ
2. ส่ง Location เข้าบอท (Issue #37) ตรวจสอบว่าระบบตอบกลับ "⏳ กำลังประมวลผล..." ทันที และแก้ไขตัวเองเป็นผลลัพธ์พยากรณ์จริงเมื่อทำงานสำเร็จ
3. ทดสอบการดึงข้อมูลจาก Webhook (Issue #38) โดยใช้ Mock Data ตรวจสอบผลลัพธ์
4. สำหรับ Issue #26 ให้ใช้ `/devmock rain` เปลี่ยนพารามิเตอร์ฝนแบบรุนแรงน้อย (ติด Cooldown) แล้วตามด้วยแบบฝนรุนแรงมาก และดูว่าการแจ้งเตือนที่ 2 จะทะลุ Cooldown หรือไม่
