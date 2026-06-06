# แผนการพัฒนา (Implementation Plan) - Issue #2: FastAPI On-demand Routers

เอกสารฉบับนี้อธิบายแผนการพัฒนาระบบ API Router แบบ On-demand สำหรับดึงข้อมูลพยากรณ์ฝนตามพิกัด (lat, lng) โดยอิงจาก Service ที่มีอยู่แล้ว ได้แก่ `RainbowService` และ `RainViewerService` 
และจะยึดหลัก **TDD (Red -> Green -> Refactor)** อย่างเคร่งครัดตามข้อกำหนดของโปรเจกต์

## User Review Required

> [!IMPORTANT]
> - Endpoint ที่ออกแบบไว้คือ `GET /api/v1/weather/predict?lat=...&lng=...` เหมาะสมหรือไม่ หรืออยากให้เป็น `POST` แล้วรับ Request Body แทนครับ? (แนะนำ `GET` สำหรับการดึงข้อมูลแบบไม่มี side-effect)
> - ต้องการให้เพิ่ม `RainViewerService` ใน response ด้วยไหมครับ หรือใช้แค่ `RainbowService` สำหรับทำ prediction อย่างเดียวไปก่อนสำหรับ API นี้?

## Proposed Changes

### สถาปัตยกรรม (Architecture)
เนื่องจากเรายังไม่มีตัวเข้าแอป (Entry point) ของ FastAPI เราจะต้องสร้างไฟล์พื้นฐานขึ้นมาใหม่ดังนี้

---

### Backend App
เราจะจัดเรียงไฟล์ตามโครงสร้างของ FastAPI

#### [NEW] [main.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/main.py)
- สร้าง FastAPI application instance
- ใส่ Metadata (Title, Description, Version)
- Include Router จาก `app.routers.weather`

#### [NEW] [weather.py (schemas)](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/schemas/weather.py)
- สร้าง Pydantic Models สำหรับ Response (เช่น `PredictionResponse`, `PredictionItem`)
- ช่วยให้ FastAPI สร้าง Swagger Document อัตโนมัติและจัดการเรื่อง Data Validation

#### [NEW] [weather.py (routers)](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/routers/weather.py)
- สร้าง APIRouter `router = APIRouter(prefix="/api/v1/weather", tags=["weather"])`
- เพิ่ม Endpoint `GET /predict` 
- ข้างใน Endpoint จะมีการเรียกใช้งาน `RainbowService.predict_rain_by_location(lat, lng)`

#### [NEW] [test_api_weather.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/tests/test_api_weather.py)
- สร้าง Test cases โดยใช้ `httpx.AsyncClient` หรือ `fastapi.testclient.TestClient`
- ทดสอบเคสปกติ (Valid lat, lng) ข้อมูลต้องกลับมาเป็น JSON structure ตาม schema
- ทดสอบเคสกรอกข้อมูลผิด (Invalid parameters) ต้องโดนดัก 422 Unprocessable Entity
- **(TDD):** เราจะเขียนและรันไฟล์นี้ให้ Failed (Red) ก่อน แล้วค่อยลงมือเขียน Code ฝั่งแอปเพื่อให้ Passed (Green)

## Verification Plan

### Automated Tests
- รัน `pytest backend/tests/test_api_weather.py -v` (ต้องผ่าน 100%)
- ทดสอบด้วย coverage (ถ้ามีตั้งค่าไว้) เพื่อให้แน่ใจว่า test คลุมโค้ดฝั่ง Router

### Manual Verification
- รันเซิร์ฟเวอร์ด้วย `uvicorn app.main:app --reload`
- เข้าไปที่ `http://127.0.0.1:8001/docs` (Swagger UI) ลองกรอก `lat=17.1664` และ `lng=104.1486` และดูผลลัพธ์
