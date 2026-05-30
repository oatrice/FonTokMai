# Walkthrough: การอัปเดตระบบให้รองรับ Rainbow Weather API ของจริง (Issue #17)

## สิ่งที่ทำไปแล้ว (Changes Made)
1. **อัปเดตชุดทดสอบ (Red Phase)**
   - เข้าไปแก้ไข `backend/tests/test_services.py` 
   - เปลี่ยน `mock_response` ให้จำลองการตอบกลับ (Response) ของ Rainbow API เวอร์ชันล่าสุด (0.34.0) ซึ่งมีโครงสร้างเป็น `{ "forecast": [...], "summary": {...} }`
   - รัน Test แล้วพบว่า **พังทั้งหมด** (Failed) ตามคาด เพราะระบบเดิมยังอ่านค่าจากคีย์ `predictions` 

2. **ปรับปรุงโค้ดโปรดักชัน (Green Phase & Refactor)**
   - แก้ไข `RainbowService` ในไฟล์ `backend/app/services/rainbow.py`
   - **เปลี่ยน Endpoint URL:** ไปใช้ `https://api.rainbow.ai/nowcast/v1/precip-global/{longitude}/{latitude}`
   - **เปลี่ยนวิธีอ่านข้อมูล:** อ่านค่า `forecast`, `timestampBegin`, และ `precipRate`
   - **แปลงค่า (Transform):** แปลงค่า Unix Timestamp กลับไปเป็น ISO 8601 (`2026-05-29T14:00:00Z`) เพื่อให้เข้ากันได้กับระบบแจ้งเตือนตัวเดิมโดยไม่ต้องไปรื้อโครงสร้างส่วนอื่น
   - **ดึงข้อมูล Intensity:** ใช้ `summary.intensity` ที่ API ส่งมาให้โดยตรง (เช่น light, moderate, heavy) เพื่อความแม่นยำ 
   - คงค่า Header `Ocp-Apim-Subscription-Key` ไว้ตามที่คุณยืนยันมา

## สิ่งที่ได้ทดสอบ (What was tested)
- รันคำสั่ง `pytest backend/tests/ -v` 
- **ผลลัพธ์:** โค้ดที่อัปเดตใหม่สามารถประมวลผล Mock Data ได้ถูกต้อง และ Test Case ทั้งหมด 20 ตัว **ผ่านฉลุย (Passed 100%)**

> [!TIP]
> ตอนนี้คุณสามารถ Push โค้ดใน Branch `feat/17-update-rainbow-api` ขึ้นไปบน GitLab เพื่อให้ CI/CD รัน และอัปเดตขึ้น Cloud Run ได้เลยครับ ฝนมายังจะได้ดึงข้อมูล API ได้แบบถูกต้อง 100% สักที!
