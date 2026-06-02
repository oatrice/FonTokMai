# เป้าหมาย

เพิ่มฟีเจอร์ "Support multiple saved locations per user (e.g. Home, Work)" (Issue #9) เพื่อให้ผู้ใช้สามารถบันทึกพิกัดได้หลายสถานที่ เช่น บ้าน (Home), ที่ทำงาน (Work) หรือพิกัดทั่วไป (Default) และให้ระบบแจ้งเตือนฝนตกล่วงหน้าแยกตามแต่ละสถานที่ได้

## ข้อควรระวัง (User Review Required)

> [!WARNING]
> การเปลี่ยนแปลงนี้จะแก้ไขโครงสร้างของ Callback Data ใน Inline Keyboard เพื่อส่งชื่อสถานที่ (`name`) ไปด้วย ซึ่งต้องรักษาความยาวของ Callback Data ไม่ให้เกิน 64 bytes ตามข้อจำกัดของ Telegram
> เช่น `loc_save_home_inf_13.1_100.1` 

## คำถามเพิ่มเติม (Open Questions)

- **UI ในการบันทึกพิกัด:** เมื่อผู้ใช้ส่ง Location เข้ามาในแชท แทนที่จะถามแค่ "จำ 2 เดือน" หรือ "จำตลอดไป" เราจะให้เลือกสถานที่เลย เช่น `[🏠 บันทึกเป็น บ้าน]`, `[💼 บันทึกเป็น ที่ทำงาน]`, `[📍 บันทึกเป็น Default]` โดยให้ **จำตลอดไป (Forever)** เป็นค่าเริ่มต้นทั้งหมดเพื่อให้ UI ไม่ซับซ้อนเกินไป (ลดจำนวนปุ่มลง) หรือยังต้องการให้เลือกวันหมดอายุด้วยครับ? (ในแผนเบื้องต้นจะยึดตาม Retention เดิม แต่เพิ่มปุ่มแยกตามประเภทสถานที่)
- **การแจ้งเตือน (Proactive Alert):** ข้อความที่แจ้งเตือนจะถูกปรับให้ระบุชื่อสถานที่ด้วย เช่น `🌧️ ฝนกำลังเคลื่อนมาที่ 🏠 Home ของคุณ...`

## การเปลี่ยนแปลงที่นำเสนอ

### 1. Database Model & Repository

#### [MODIFY] [models.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/models.py)
- เพิ่มฟิลด์ `name = Column(String, default="default", nullable=False)` ใน `UserLocation`
- นำ `unique=True` ออกจาก `chat_id` เพราะ 1 ผู้ใช้มีได้หลายพิกัด

#### [MODIFY] [base.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/repositories/base.py)
- ปรับปรุง Signature ของฟังก์ชัน:
  - `get_location(chat_id: int, name: str = "default")`
  - `save_location(..., name: str = "default")`
  - `delete_location(chat_id: int, name: str = "default")`
- เพิ่มฟังก์ชัน `get_user_locations(chat_id: int) -> list[UserLocation]`

#### [MODIFY] [sqlite.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/repositories/sqlite.py) และ [firestore.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/repositories/firestore.py)
- อัปเดตลอจิกตาม Interface ใหม่ 
- สำหรับ Firestore จะเปลี่ยน Document ID เป็น `{chat_id}_{name}`

### 2. Telegram Bot Webhook & UI

#### [MODIFY] [webhook.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/routers/webhook.py)
- **เมื่อได้รับ Location:** สร้างปุ่มให้เลือกรูปแบบสถานที่ `[🏠 บ้าน]`, `[💼 ที่ทำงาน]`, `[📍 ตำแหน่งทั่วไป]` พร้อม Callback แบบใหม่ 
- **คำสั่ง `/mylocation`:** แสดงรายการพิกัดทั้งหมดของผู้ใช้ที่ดึงจาก `get_user_locations()` พร้อมปุ่มลบ `[🗑️ ลบ บ้าน]`, `[🗑️ ลบ ที่ทำงาน]` แยกทีละรายการ
- **การจัดการ Callback Query:** อัปเดต parser ให้รองรับ callback data รูปแบบใหม่

### 3. Background Alert Scheduler

#### [MODIFY] [scheduler_tasks.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/scheduler_tasks.py)
- เมื่อแจ้งเตือน ให้ตรวจสอบ `loc.name` หากไม่ใช่ "default" ให้นำมาใส่ในข้อความเพื่อระบุว่าฝนกำลังจะตกที่ไหน (เช่น "ฝนกำลังตกที่ บ้าน ของคุณ")

### 4. Tests

#### [MODIFY] [test_repositories.py, test_firestore.py, test_db.py, test_webhook.py, test_scheduler.py]
- อัปเดต unit tests ทั้งหมดเพื่อให้สอดคล้องกับพารามิเตอร์ใหม่ และรับรองกรณีที่มีหลาย location ใน 1 `chat_id`

## แผนการทดสอบและยืนยันผล (Verification Plan)

### Automated Tests
- รัน `pytest backend/tests/` ทั้งหมด เพื่อตรวจยืนยันว่าการแก้ไข Repository และ Router (Red -> Green -> Refactor) ผ่านทั้งหมด 100%

### Manual Verification
- ขอให้ผู้ใช้ส่งพิกัดมา 2 ที่ และตั้งเป็น Home และ Work ตามลำดับ
- พิมพ์ `/mylocation` เพื่อตรวจสอบว่าระบบแสดงผลรายการ 2 ที่ถูกต้อง
- ทดลองกดลบออก 1 ที่ และตรวจสอบผลลัพธ์
