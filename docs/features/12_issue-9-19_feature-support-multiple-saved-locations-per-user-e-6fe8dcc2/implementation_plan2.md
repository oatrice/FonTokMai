# แผนการพัฒนา Feature: Developer Mock Mode for Background Scheduler (Issue #19)

เป้าหมายคือการสร้างโหมด Mock สถานะฝนตก (Mock State) เพื่อใช้ทดสอบการทำงานของ Background Scheduler และแจ้งเตือนผ่าน Telegram โดยไม่ต้องรอให้ฝนตกจริงๆ (สามารถทำได้เฉพาะนักพัฒนาที่อยู่ใน `DEVELOPER_CHAT_IDS`)

## User Review Required

- **การแยก Table/Collection สำหรับข้อมูล Mock**: เพื่อไม่ให้กระทบกับข้อมูล `UserLocation` ปัจจุบัน (ซึ่ง 1 User อาจมีหลาย Location) จะมีการสร้าง Table ใหม่ใน SQLite และ Collection ใหม่ใน Firestore ชื่อ `dev_mocks` เพื่อเก็บ `mock_state` ตาม `chat_id` แบบ 1-to-1
- การใช้คำสั่ง `/devmock` จะมี 3 รูปแบบ:
  1. `/devmock rain` - จำลองว่าฝนตกหนัก
  2. `/devmock clear` - จำลองว่าท้องฟ้าแจ่มใส
  3. `/devmock off` - ปิดโหมดจำลอง (กลับไปใช้ API ของ Rainbow.ai ตามปกติ)

## Proposed Changes

---

### Database Models

#### [NEW] [models.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/models.py)
- เพิ่ม SQLAlchemy Model `DeveloperMock`
- ประกอบด้วย `chat_id` (Primary Key / BigInteger) และ `state` (String) 

---

### Repositories (Database Access)

#### [MODIFY] [base.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/repositories/base.py)
- เพิ่ม Abstract methods ลงใน `LocationRepository`:
  - `async def get_mock_state(self, chat_id: int) -> Optional[str]: ...`
  - `async def set_mock_state(self, chat_id: int, state: Optional[str]) -> None: ...`

#### [MODIFY] [sqlite.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/repositories/sqlite.py)
- Implement `get_mock_state` และ `set_mock_state` สำหรับ SQLite โดยใช้ตาราง `DeveloperMock`
- จัดการสร้างข้อมูลใหม่ (Add) หากไม่เคยมี หรือลบออก (Delete) หาก `state` เป็น None (ปิด Mock)

#### [MODIFY] [firestore.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/repositories/firestore.py)
- Implement `get_mock_state` และ `set_mock_state` 
- เก็บลงใน `self.db.collection('dev_mocks').document(str(chat_id))` 
- กำหนดให้เซฟเป็น `{"state": state}` และสั่งลบ Document หาก `state` เป็น None

---

### Weather Service

#### [MODIFY] [rainbow.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/services/rainbow.py)
- เพิ่ม Parameter ใหม่ `mock_state: Optional[str] = None` ลงใน method `predict_rain_by_location`
- หาก `mock_state == "rain"` ให้คืนค่า Dictionary ที่จำลองว่ามีฝนตกหนัก 60 นาที (Intensity = "หนัก (Heavy)")
- หาก `mock_state == "clear"` ให้คืนค่า Dictionary ว่า "ไม่มีฝน (No Rain)"
- หากเป็น `None` ให้ยิง API ไปที่ Rainbow.ai ตามปกติ

---

### Business Logic

#### [MODIFY] [webhook.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/routers/webhook.py)
- เพิ่มคำสั่งย่อยใน `telegram_webhook` เพื่อดักจับ `/devmock`
- อนุญาตให้ใช้งานเฉพาะ `chat_id` ที่อยู่ใน `DEVELOPER_CHAT_IDS`
- เมื่อพิมพ์คำสั่ง ให้เรียกใช้ `await repo.set_mock_state(...)` และตอบกลับยืนยันทาง Telegram
- เมื่อผู้ใช้ส่ง `Location` เข้ามา ให้ดึง `mock_state` และส่งเป็น parameter เข้าไปใน `predict_rain_by_location` ด้วย (เพื่อให้การกดเช็คแมนนวลก็ทดสอบ mock ได้)

#### [MODIFY] [scheduler_tasks.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/scheduler_tasks.py)
- ใน Loop ของ `get_active_locations()` ให้ดึง `mock_state = await repo.get_mock_state(loc.chat_id)`
- นำ `mock_state` ส่งผ่าน parameter เข้า `rainbow_svc.predict_rain_by_location(...)` 
- เพื่อให้ Scheduler ได้รับ Mock ข้อมูล และประมวลผลการแจ้งเตือนฝนตกได้ทันที

---

## Verification Plan

### Manual Verification
1. เพิ่ม User ID ของตัวเองเข้าในไฟล์ `.env` ตรง `DEVELOPER_CHAT_IDS` (ถ้ายังไม่มี)
2. พิมพ์คำสั่ง `/devmock rain` ใน Telegram และตรวจสอบว่าบอทตอบกลับว่าเปิดโหมด Mock ฝนตกแล้ว
3. สั่งรัน `/api/v1/cron/check-rain` ผ่าน `curl` (เหมือน Step 10)
4. ยืนยันว่าแอปพลิเคชันแจ้งเตือนมาใน Telegram ว่าจะมีฝนตกหนัก!
5. พิมพ์ `/devmock clear` สั่งรัน `curl` อีกครั้ง และดูว่าใน Log ต้องไม่มีการแจ้งเตือน
6. พิมพ์ `/devmock off` เพื่อกลับเข้าสู่โหมดปกติ
