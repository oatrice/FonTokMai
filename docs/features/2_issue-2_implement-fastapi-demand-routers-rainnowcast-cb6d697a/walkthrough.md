# Walkthrough: FastAPI On-demand Routers (Issue #2)

เอกสารฉบับนี้สรุปการทำงานที่สำเร็จเรียบร้อยสำหรับการสร้างระบบ API แบบ On-demand ในแอปพลิเคชัน FastAPI เพื่อใช้สำหรับดึงข้อมูลพยากรณ์ฝน

## การเปลี่ยนแปลงที่เกิดขึ้น (Changes Made)

1. **สร้าง Pydantic Schemas (`backend/app/schemas/weather.py`)**
   - เพิ่ม `PredictionItem` และ `PredictionResponse` เพื่อรองรับการทำ Data Validation และช่วยให้ FastAPI นำไปสร้าง Swagger Document ได้โดยอัตโนมัติ
   
2. **สร้าง API Endpoint (`backend/app/routers/weather.py`)**
   - สร้าง Endpoint ใหม่: `GET /api/v1/weather/predict?lat=...&lng=...`
   - ทำการเรียกใช้ `RainbowService.predict_rain_by_location()` เพื่อดึงผลลัพธ์พยากรณ์ล่วงหน้า
   - มีระบบ Error Handling (HTTP 500) ครอบไว้เผื่อกรณีที่ Service ภายนอกมีปัญหา

3. **เตรียมตัวรัน FastAPI Application (`backend/app/main.py`)**
   - สร้าง Instance ของแอปพลิเคชัน FastAPI 
   - กำหนด Title, Description, และ Version สำหรับ API
   - เชื่อมต่อ (include) Router ที่เราเพิ่งสร้างขึ้น และเพิ่ม `GET /health` สำหรับการทำ Health check
   
4. **กระบวนการ TDD & Automated Tests (`backend/tests/test_api_weather.py`)**
   - เขียน Failing Test ก่อน เพื่อดักจับกรณีที่ไม่ได้ระบุพิกัด และกรณีปกติ
   - ใช้งาน `TestClient` ของ FastAPI และใช้ `AsyncMock` จาก `unittest.mock` เพื่อจำลองการเรียกหา `RainbowService` โดยไม่ต้องยิง API จริง
   - ผลทดสอบผ่านครบ 100% (6 Passed รวมเทสต์ตัวเดิมของ Services)

## การตรวจสอบ (Validation Results)

- **Unit Tests:** `pytest` รันผ่านทั้งหมด 6 items (รวมทั้ง Services เดิม และ Router ใหม่)
- **TDD Enforcement:** ดำเนินการผ่าน Red (ตอนที่ยังไม่มี `main.py`) $\rightarrow$ Green (โค้ดรันผ่าน) $\rightarrow$ Refactor (จัดระเบียบโครงสร้าง Router และ Schema แยกโฟลเดอร์)

## Note สำหรับอนาคต
โครงสร้างพร้อมสำหรับการพัฒนาต่อยอดเพื่อรวม `RainViewerService` เข้ามาด้วย `asyncio.gather` ตามที่ตกลงกันไว้ครับ (ถูกเก็บรายการไว้ใน `task.md`)
