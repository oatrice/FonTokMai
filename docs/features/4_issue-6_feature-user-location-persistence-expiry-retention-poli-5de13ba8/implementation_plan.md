# การเพิ่มฟีเจอร์จดจำตำแหน่งผู้ใช้งานพร้อมระบบหมดอายุอัตโนมัติ (Issue #6)

เป้าหมายของแผนนี้คือการเพิ่มระบบฐานข้อมูลแบบ SQLite สำหรับบันทึกตำแหน่ง (Location) ของผู้ใช้ที่ส่งเข้ามาผ่าน Telegram Webhook โดยผู้ใช้สามารถเลือกได้ว่าจะให้ระบบจดจำตำแหน่งเป็นเวลา 2 เดือน, ตลอดไป หรือไม่จดจำเลย เพื่อรองรับระบบแจ้งเตือนฝนตกอัตโนมัติ (Proactive Alerts) ในอนาคต ตามแนวทาง Privacy-First ที่เน้นเก็บข้อมูลเท่าที่จำเป็นและให้อำนาจตัดสินใจกับผู้ใช้

## User Review Required

> [!IMPORTANT]
> - ระบบฐานข้อมูลจะใช้ `SQLite` ผ่าน `SQLAlchemy` (Async Driver: `aiosqlite`) เนื่องจากเหมาะกับขนาดและสเกลปัจจุบันของแอปพลิเคชัน
> - Telegram มีข้อจำกัดเรื่อง `callback_data` ที่ส่งผ่าน Inline Keyboard ว่าห้ามเกิน 64 bytes ดังนั้นข้อมูลที่จะส่งไปพร้อมปุ่มกดจะเป็นเพียงคำสั่งสั้นๆ เช่น `loc_2m_<lat>,<lng>` เพื่อไม่ให้เกินโควต้า
> - เพื่อความแม่นยำและไม่เปลืองพื้นที่ใน Callback Data ผมจะปัดเศษของพิกัดให้เป็นทศนิยม 4 ตำแหน่ง (ระดับความแม่นยำประมาณ 11 เมตร ซึ่งเพียงพอสำหรับฝน) ใน `callback_data` 
> - **สอดคล้องกับ Feedback**: ปุ่มกดทั้งหมดจะถูกส่งไปพร้อมกับข้อความพยากรณ์อากาศเลยในกรอบเดียวกัน (Inline)
> - **สอดคล้องกับ Feedback**: ระบบจะเช็คข้อมูลพิกัดเก่าของผู้ใช้ก่อน หากมีข้อมูลเก่าอยู่แล้วจะปรับข้อความและปุ่มกดให้เป็นแนวทางการ "อัปเดต" หรือ "ลบของเดิมทิ้ง"
> - **สอดคล้องกับ Feedback**: จะเพิ่มคำสั่ง `/mylocation` เพื่อให้ผู้ใช้เช็คข้อมูลตำแหน่งปัจจุบันที่บันทึกไว้ได้

## Proposed Changes

### Database Setup & Models

เราจะสร้างโครงสร้างพื้นฐานสำหรับฐานข้อมูลและ Model ก่อน

#### [NEW] [database.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/database.py)
- ตั้งค่าการเชื่อมต่อ SQLite แบบ Asynchronous (`aiosqlite`)
- สร้าง `async_sessionmaker` และฟังก์ชัน `get_db` สำหรับ Dependency Injection

#### [NEW] [models.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/models.py)
- สร้าง SQLAlchemy Model ชื่อ `UserLocation`
- ฟิลด์: `id` (Integer), `chat_id` (BigInteger, unique), `platform` (String, default="telegram"), `latitude` (Float), `longitude` (Float), `retention_type` (String: ONCE, TWO_MONTHS, FOREVER), `expires_at` (DateTime nullable)

#### [MODIFY] [requirements.txt](file:///Users/oatrice/Software-projects/FonMaYang/backend/requirements.txt)
- เพิ่ม dependency: `sqlalchemy` และ `aiosqlite`

#### [MODIFY] [main.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/main.py)
- เพิ่ม Lifespan event เพื่อให้สร้างตารางในฐานข้อมูลตอนที่แอปพลิเคชันเริ่มต้นทำงานโดยอัตโนมัติ (ถ้ายังไม่มีตาราง)

### Webhook Updates

#### [MODIFY] [webhook.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/routers/webhook.py)
- เพิ่มฟังก์ชันจัดการคำสั่ง **`/mylocation`**:
  - เมื่อได้รับคำสั่งนี้ ระบบจะตรวจสอบ `UserLocation` ในฐานข้อมูล
  - หากพบพิกัดเดิม จะตอบกลับด้วยรายละเอียดพิกัดและเวลาหมดอายุ พร้อมปุ่ม Inline Keyboard **"🗑️ ลบพิกัดเดิม"** (`callback_data`: `loc_del`)
  - หากไม่พบ จะตอบกลับว่า "คุณยังไม่ได้บันทึกตำแหน่งใดๆ ไว้"

- ปรับปรุงฟังก์ชัน `process_telegram_location`: 
  - ก่อนเตรียมคำตอบ ให้เช็คว่าผู้ใช้ (chat_id) นี้มีตำแหน่งเก่าบันทึกไว้แล้วหรือไม่
  - เมื่อสรุปคำพยากรณ์เสร็จ ให้เพิ่มข้อความต่อท้าย:
    - กรณี **ยังไม่มีพิกัดเดิม**: "คุณต้องการให้ระบบจดจำตำแหน่งนี้สำหรับการแจ้งเตือนฝนตกอัตโนมัติไหม?"
      - ⏳ จำ 2 เดือน (`callback_data`: `loc_2m_<lat>,<lng>`)
      - ♾️ จำตลอดไป (`callback_data`: `loc_inf_<lat>,<lng>`)
      - ❌ ไม่เป็นไร (`callback_data`: `loc_no`)
    - กรณี **มีพิกัดเดิมอยู่แล้ว**: "คุณมีพิกัดเดิมบันทึกไว้อยู่แล้ว ต้องการอัปเดตเป็นพิกัดนี้ หรือลบของเดิมทิ้งหรือไม่?"
      - 🔄 อัปเดต (จำ 2 เดือน) (`callback_data`: `loc_2m_<lat>,<lng>`)
      - 🔄 อัปเดต (จำตลอดไป) (`callback_data`: `loc_inf_<lat>,<lng>`)
      - 🗑️ ลบพิกัดเดิม (`callback_data`: `loc_del`)

- เพิ่มส่วนจัดการ `callback_query` ภายใน `telegram_webhook`:
  - `loc_2m_<lat>,<lng>`: บันทึก/อัปเดต `UserLocation` พร้อมระบุ `expires_at` (+60 วัน)
  - `loc_inf_<lat>,<lng>`: บันทึก/อัปเดต `UserLocation` พร้อมระบุ `expires_at` เป็น `NULL`
  - `loc_no`: ไม่ทำอะไร หรือลบข้อความปุ่มออกไปเฉยๆ
  - `loc_del`: ค้นหาและลบ `UserLocation` ของผู้ใช้ออก และตอบกลับว่า "ลบข้อมูลพิกัดเดิมของคุณเรียบร้อยแล้ว"
  - จบด้วยการเรียก `answerCallbackQuery` และ `editMessageReplyMarkup` เพื่อเอาปุ่มออกป้องกันการกดซ้ำ

### Testing (TDD)

#### [NEW] [test_db.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/tests/test_db.py)
- เขียน Unit Test สำหรับโมเดลและฟังก์ชันการสืบค้นข้อมูล ฐานข้อมูล (Save, Get, Delete)

#### [MODIFY] [test_apis.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/tests/test_apis.py)
- ทดสอบ Workflow เมื่อมีการส่งพิกัด:
  - กรณีผู้ใช้ใหม่ -> ส่งปุ่มแบบหนึ่ง
  - กรณีผู้ใช้เก่า -> ส่งปุ่มที่มีตัวเลือก "อัปเดต/ลบ"
- ทดสอบการกด `callback_query`: ตรวจสอบว่าแก้ไข DB ได้ถูกต้อง
- ทดสอบคำสั่ง `/mylocation` 

## Verification Plan

### Automated Tests
- รัน `pytest -v` ด้วยหลักการ Red -> Green -> Refactor เพื่อให้แน่ใจว่าฟังก์ชันทุกอย่างครอบคลุม Business Logic ตามที่กำหนด

### Manual Verification
- รัน `uvicorn` และทดสอบด้วยการยิง Payload ผ่าน cURL หรือ Postman
- ทดลองจำลองการส่ง Location แบบผู้ใช้ใหม่
- จำลองการกดปุ่ม "จำ 2 เดือน" (ยิง `callback_query`)
- ทดลองจำลองการส่ง Location อีกครั้ง (ระบบต้องตรวจเจอว่ามีของเก่าและเปลี่ยนปุ่มเป็นอัปเดต)
- จำลองการพิมพ์ `/mylocation`
- จำลองการกดปุ่ม "ลบพิกัดเดิม"
