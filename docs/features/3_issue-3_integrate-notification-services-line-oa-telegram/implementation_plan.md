# แผนการพัฒนา Issue #3: Integrate Notification Services (Telegram Webhook)

เป้าหมายหลักคือการสร้าง Webhook สำหรับรับพิกัดจากผู้ใช้ (ผ่าน Telegram) และส่งผลทำนายฝน (ETA) กลับไป โดยยึดหลักการ Privacy-First (ไม่บันทึกพิกัดลงฐานข้อมูล, ทำงานแบบ On-Demand)
สำหรับ Line OA จะถูกแยกออกไปทำเป็น Issue แยกต่างหากในภายหลัง

## User Review Required

> [!IMPORTANT]  
> **เรื่อง Privacy-First:** ระบบจะไม่มีการสร้างตารางบันทึกพิกัด (`latitude`, `longitude`) ของผู้ใช้ลงใน Database ใดๆ ทั้งสิ้น ระบบจะรับพิกัดมาแบบ On-demand จาก Webhook, นำไปเรียก API `RainbowService`, จัดรูปประโยค, ส่งกลับให้ผู้ใช้, และจบการทำงานทันที

## Open Questions

> [!WARNING]  
> 1. **Telegram SDK vs Raw HTTP:** เราจะใช้ไลบรารีอย่าง `python-telegram-bot` หรือจะใช้ `httpx` ยิง API โดยตรงเพื่อความเบาของระบบ? (แผนนี้เสนอให้ใช้ `httpx` เพื่อไม่ให้บวม)
> 2. **Telegram Bot Token:** ในขั้นนี้เราจะตั้งค่าใน `.env` เพื่อดึงค่า `TELEGRAM_BOT_TOKEN` ในการใช้ทดสอบการทำงานจริงเลยหรือไม่ หรือ Mock 100% ไปก่อน?

## Proposed Changes

การทำงานจะอิงหลัก TDD (Red -> Green -> Refactor) โดยจะเริ่มเขียนเทสต์ก่อนเสมอ

### Routers & API

#### [NEW] `backend/tests/test_webhook.py`
- เพิ่มชุดทดสอบ (Failing Tests) สำหรับ endpoint `/api/v1/webhook/telegram`
- จำลอง (Mock) Webhook Payload ที่ส่งมาจาก Telegram (ประเภท Message แบบมีพิกัด Location)
- จำลองการทำงานของ `RainbowService` ด้วย `new_callable=AsyncMock` ตามข้อตกลง
- ทดสอบว่าระบบเรียก `RainbowService` และพยายามส่งข้อความกลับไปยังผู้ใช้ (ผ่าน `httpx` mock ไปยัง `api.telegram.org`) ได้อย่างถูกต้อง

#### [NEW] `backend/app/routers/webhook.py`
- สร้าง FastAPI router สำหรับ Webhook
- สร้าง endpoint `POST /api/v1/webhook/telegram`
- ตรวจสอบว่า Event ที่เข้ามาเป็น Message ที่แนบ `location` หรือไม่
- ดึงค่า Latitude, Longitude จาก Location Message
- เรียกใช้งาน `RainbowService.predict_rain_by_location(lat, lng)`
- ประมวลผลลัพธ์ (เช่น ฝนจะตกใน 20 นาที) และส่ง HTTP Post กลับไปหา Telegram API (`sendMessage`) พร้อมแนบ `chat_id` ที่ตอบกลับ

#### [MODIFY] `backend/app/main.py`
- เพิ่ม `app.include_router(webhook.router)` เพื่อเชื่อมต่อ Webhook router เข้ากับแอปหลัก

## Verification Plan

### Automated Tests
- รัน `pytest backend/tests/test_webhook.py -v` เพื่อยืนยันว่าโค้ดผ่านเงื่อนไข TDD ครบถ้วน
- ระบบจะต้องไม่มีการเรียกใช้ API จริง ๆ ของ Telegram หรือ Rainbow ในขณะรันเทสต์ (ใช้ Mock 100%)

### Manual Verification
- สามารถทดลองยิง `curl` POST request หน้าตาเหมือน Telegram Webhook มายัง `http://localhost:8000/api/v1/webhook/telegram` เพื่อดู response หรือตรวจสอบ log ว่าฝั่ง Backend ดำเนินการถูกต้องหรือไม่
