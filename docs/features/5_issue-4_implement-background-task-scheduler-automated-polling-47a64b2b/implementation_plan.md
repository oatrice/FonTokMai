# แผนการทำงาน Issue #4: Implement Task Scheduler & Proactive Automation

เป้าหมายคือการเปลี่ยนระบบ FonMaYang จากรูปแบบ On-demand (รอผู้ใช้ทัก) ให้กลายเป็น Proactive Alert (แจ้งเตือนอัตโนมัติเมื่อฝนกำลังจะตก) 
โดยใช้ APScheduler ทำงานในเบื้องหลังของ FastAPI และตรวจสอบพิกัดของผู้ใช้งานทั้งหมดทุกๆ 5 นาที

## สิ่งที่ต้องผู้ใช้รีวิว / ตรวจสอบ (User Review Required)

> [!IMPORTANT]
> - เนื่องจากไม่มีการใช้ Alembic ในการจัดการ Database Migration การเพิ่มคอลัมน์ `last_alerted_at` จะต้องใช้คำสั่ง SQL `ALTER TABLE` ตรงๆ กับไฟล์ `fonmayang.db` เพื่อไม่ให้ข้อมูลผู้ใช้เก่าหาย หรือถ้าหากเป็นเพียง Development Database ก็สามารถลบไฟล์ `.db` ทิ้งเพื่อให้ระบบสร้างใหม่ได้
> - รอบการแจ้งเตือน (Spam Prevention) ตอนนี้กำหนดไว้ว่า **หากมีการแจ้งเตือนฝนตกไปแล้ว จะไม่แจ้งซ้ำภายใน 2 ชั่วโมง** เพื่อป้องกันไม่ให้ผู้ใช้โดนสแปมข้อความทุก 5 นาที

## แผนการเปลี่ยนแปลง (Proposed Changes)

### 1. Dependencies
#### [MODIFY] [requirements.txt](file:///Users/oatrice/Software-projects/FonMaYang/backend/requirements.txt)
- เพิ่ม `apscheduler` เข้าไปในรายการ dependencies

### 2. Database Models
#### [MODIFY] [backend/app/models.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/models.py)
- เพิ่มคอลัมน์ `last_alerted_at = Column(DateTime, nullable=True)` ในคลาส `UserLocation` เพื่อเก็บเวลาเตือนครั้งล่าสุด

### 3. Services Refactoring
#### [NEW] [backend/app/services/telegram.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/telegram.py)
- สร้างฟังก์ชัน `send_telegram_message(chat_id: int, text: str)` เพื่อให้สามารถส่งข้อความจาก Background Task ได้ง่ายขึ้น
- จะทำการย้ายโค้ดบางส่วนจาก `webhook.py` มาใช้ฟังก์ชันนี้แทนในภายหลัง (Refactor)

#### [MODIFY] [backend/app/services/location.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/location.py)
- เพิ่มฟังก์ชัน `get_active_locations(session: AsyncSession)` เพื่อดึงพิกัดทั้งหมดที่ยังไม่หมดอายุ
- เพิ่มฟังก์ชัน `update_last_alerted_at(session: AsyncSession, chat_id: int)` เพื่ออัปเดตเวลาแจ้งเตือน

### 4. Background Scheduler
#### [NEW] [backend/app/scheduler_tasks.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/scheduler_tasks.py)
- สร้างงาน (Task) ประจำที่จะถูกรันทุก 5 นาที
- ลอจิก: 
  1. ดึงพิกัดที่แอคทีฟทั้งหมด
  2. วนลูปตรวจสอบฝนผ่าน `RainbowService` ของแต่ละพิกัด
  3. หากเวลาที่ฝนจะตก (ETA) <= 60 นาที ให้ตรวจสอบ `last_alerted_at` ว่ายังไม่เคยเตือนหรือเตือนไปเกิน 2 ชั่วโมงแล้วหรือยัง
  4. หากเข้าเงื่อนไข ให้ส่งข้อความแจ้งเตือนผ่าน `send_telegram_message` และอัปเดต `last_alerted_at`

### 5. FastAPI Application
#### [MODIFY] [backend/app/main.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/main.py)
- เพิ่ม `AsyncIOScheduler` เข้ามาในฟังก์ชัน `lifespan`
- กำหนดให้รัน `scheduler_tasks.py` ทุกๆ 5 นาที (`cron` หรือ `interval`)
- สั่ง `scheduler.start()` ก่อน `yield` และ `scheduler.shutdown()` หลัง `yield`

## แผนการตรวจสอบและทดสอบ (Verification Plan)

### Automated Tests (TDD)
> [!NOTE]
> จะปฏิบัติตาม TDD อย่างเคร่งครัด (Red -> Green -> Refactor)
- **[NEW] `backend/tests/test_scheduler.py`**: จะต้องเขียนเทสต์ครอบคลุมกรณีดังต่อไปนี้:
  - ฝนกำลังจะตก (ETA = 30 นาที) และไม่เคยเตือน -> ต้องเรียก `send_telegram_message` และอัปเดต Database
  - ฝนกำลังจะตก แต่เพิ่งแจ้งเตือนไปเมื่อ 30 นาทีที่แล้ว -> ไม่ต้องทำอะไร
  - ฝนไม่ตก (ไม่มีข้อมูล) -> ไม่ต้องทำอะไร
- จะใช้ `new_callable=AsyncMock` คู่กับ `@patch` สำหรับการ Mock Async Functions ทุกตัว

### Manual Verification
- สั่งรัน Backend (`uvicorn`) และตรวจสอบจาก log ว่า Scheduler สตาร์ทสำเร็จและทำงานทุกๆ 5 นาที
- ทดสอบเพิ่ม/อัปเดต Location ผ่านแชทบอท แล้วจำลองการมีฝนตกเพื่อดูว่าจะมีการแจ้งเตือนเข้าไปที่ Telegram หรือไม่
