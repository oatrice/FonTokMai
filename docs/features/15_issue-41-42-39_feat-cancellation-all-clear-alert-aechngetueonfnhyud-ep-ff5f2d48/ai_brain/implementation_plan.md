# แผนการพัฒนาสำหรับ Batch E (UX, Insights & Crowdsourcing)

เป้าหมายของ Batch นี้คือการเพิ่มฟีเจอร์สำหรับการยกระดับประสบการณ์ผู้ใช้งาน, การเปรียบเทียบข้อมูลจากหลายแหล่ง (Insights) และการเก็บข้อมูลจากผู้ใช้เพื่อเป็น Ground Truth (Crowdsourcing)

## User Review Required

> [!WARNING]
> การเปลี่ยนแปลงในส่วนของ Issue #39 (Interactive Ground Truth Feedback) จะมีการเพิ่ม Table ใหม่ใน SQLite และ Collection ใหม่ใน Firestore หากมีการใช้งานฐานข้อมูลใน Production อาจต้องพิจารณาเรื่อง Migration เล็กน้อย (ใน SQLite จะใช้ `Base.metadata.create_all()` ปกติ)

## Open Questions

> [!IMPORTANT]
> - **สำหรับ Issue #41 (All-Clear Alert)**: จะให้หน่วงเวลา (Debouncing) นานเท่าไรก่อนจะส่ง All-Clear เพื่อป้องกันกรณีที่พยากรณ์เคลียร์ไปแค่ 5 นาทีแล้วกลับมาตกอีก? (ค่าเริ่มต้นในแผนคือ ส่ง All-Clear ทันทีที่ระบบเช็คแล้วไม่เจอฝนตกใน 60-120 นาทีข้างหน้า ซึ่งสอดคล้องกับรอบ Cron Job ที่เช็คทุก X นาทีอยู่แล้ว)
> - **สำหรับ Issue #42 (Insights Comparison)**: ปุ่ม "เปรียบเทียบข้อมูล 3 API" ควรจะแสดงให้ผู้ใช้ทุกคนเห็นในคีย์บอร์ดตอนแจ้งเตือนฝนตกเลยหรือไม่ หรือจะเป็นคำสั่งเฉพาะ/แสดงเฉพาะ developer? (ในแผนนี้จะเพิ่มเป็นปุ่มให้ทุกคนกดดูได้เวลาต้องการเปรียบเทียบ)

## Proposed Changes

---

### Database Models

การอัปเดตโมเดลข้อมูลเพื่อรองรับการเก็บ Ground Truth

#### [MODIFY] [models.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/models.py)
- เพิ่ม `UserFeedback(Base)` เพื่อเก็บข้อมูลจากผู้ใช้งานเวลาแจ้งเตือนผิดพลาด (False Alarm)
- ฟิลด์ที่เก็บ: `id`, `chat_id`, `latitude`, `longitude`, `timestamp`, `feedback_type` (เช่น 'false_alarm'), `prediction_context` (ค่าพยากรณ์ที่ผิดพลาด)

#### [MODIFY] [base.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/repositories/base.py)
- เพิ่ม Abstract method `save_feedback(...)`

#### [MODIFY] [sqlite.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/repositories/sqlite.py)
- รัน `Base.metadata.create_all` (ถ้าจำเป็นใน setup)
- สร้างฟังก์ชัน `save_feedback` บันทึกลงตาราง `user_feedbacks`

#### [MODIFY] [firestore.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/repositories/firestore.py)
- สร้างฟังก์ชัน `save_feedback` บันทึกลง collection `user_feedbacks`

---

### Weather Manager

เพิ่มฟังก์ชันสำหรับการเรียกใช้งานหลาย API พร้อมกัน

#### [MODIFY] [weather_manager.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/weather_manager.py)
- เพิ่ม method `compare_all_apis(lat, lng, mock_state)` ซึ่งจะใช้ `asyncio.gather` เพื่อเรียก `Tomorrow.io`, `Rainbow Local` และ `Rainbow Global` พร้อมกัน
- ส่งผลลัพธ์กลับในรูปแบบ Dictionary (key ตามชื่อ API)

---

### Scheduler & Background Tasks

เพิ่มฟีเจอร์ All-Clear Alert และปุ่ม False Alarm

#### [MODIFY] [scheduler_tasks.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/scheduler_tasks.py)
- ตรวจสอบเงื่อนไข `max_rain < RAIN_TRIGGER_THRESHOLD_MM`
- เพิ่มเงื่อนไข `if loc.last_alert_max_rain > 0.0:` เพื่อดักว่าเคยส่งแจ้งเตือนฝนตกไปแล้ว
- ถ้าเป็นจริง: ส่งข้อความ All-Clear (☀️ สภาพอากาศเคลียร์แล้ว / ฝนหยุดตกแล้ว) และอัปเดต `max_rain=0.0`
- อัปเดตการสร้าง `reply_markup` เมื่อแจ้งเตือนฝน:
  - เพิ่มปุ่ม `❌ แจ้งเตือนผิดพลาด (ฝนไม่ตก)` (Callback: `fb_falsealarm_{lat}_{lng}`)
  - เพิ่มปุ่ม `📊 เทียบข้อมูล 3 API` (Callback: `compare_api_{lat}_{lng}`)

#### [MODIFY] [telegram.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/telegram.py)
- ปรับปรุง UI ของ `get_radar_inline_keyboard` หรือสร้างฟังก์ชันใหม่ในการเตรียมปุ่มต่างๆ

---

### Telegram Webhook

รองรับ Callback ใหม่จาก UI 

#### [MODIFY] [webhook.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/routers/webhook.py)
- ใน `handle_callback_query` รองรับ `data.startswith("fb_falsealarm_")`:
  - เรียกใช้ `save_feedback`
  - ตอบกลับผู้ใช้งานว่า "🙏 ขอบคุณสำหรับข้อมูล ระบบจะนำไปปรับปรุง AI ต่อไป" และเอาปุ่มทิ้ง
- รองรับ `data.startswith("compare_api_")`:
  - ตอบ loading state
  - เรียก `WeatherManager.compare_all_apis`
  - แปลงผลลัพธ์เป็นตาราง/ข้อความสรุป แล้วส่งหรือ Edit กลับไปยัง Telegram

## Verification Plan

### Automated Tests
- รัน Unit Test ในส่วนของการเรียก API ซ้ำ (TDD mode) เพื่อให้มั่นใจว่าฟังก์ชันจัดการข้อมูลทำงานได้ถูกต้อง

### Manual Verification
- ตั้งค่าให้ Mock State เป็น "rain" เพื่อรอรับการแจ้งเตือน
- กดปุ่ม "แจ้งเตือนผิดพลาด" และตรวจสอบใน SQLite/Firestore ว่ามีการบันทึกสำเร็จ
- กดปุ่ม "เปรียบเทียบข้อมูล 3 API" และดูความเร็วของการดึง (ต้องไม่หน่วงและส่งมาพร้อมกัน)
- ปรับ Mock State กลับเป็น "clear" เพื่อรอให้ระบบ Trigger ส่งข้อความ All-Clear อัตโนมัติใน Cron Job รอบถัดไป
