# Walkthrough: Open-Meteo Integration & API Accuracy Evaluation

ตามที่มีการมอบหมายให้ผนวก **Open-Meteo** และระบบ **API Evaluation** เข้ากับ `WeatherManager` งานทั้งหมดได้ดำเนินการเสร็จสิ้นเรียบร้อย โดยครอบคลุม:
- **Issue #48:** Contingency plan สำหรับการคำนวณทิศทางพายุ (Wind Vector Trajectory) กรณีที่ Xweather ล้มเหลว โดยดึงข้อมูลจาก Open-Meteo
- **Issue #49:** ประเมินความแม่นยำของแต่ละ API และใช้ Auto-Select Fallback Order เพื่อให้ได้ข้อมูลที่แม่นยำที่สุด

## 🚀 สิ่งที่พัฒนาขึ้น (Changes Made)

### 1. บริการ Open-Meteo (OpenMeteoService)
- **ไฟล์:** `backend/app/services/open_meteo.py`
- พัฒนาคลาสใหม่ `OpenMeteoService` ที่ดึงข้อมูลทิศทางลม/ความเร็วลม (`hourly`) และปริมาณฝนล่วงหน้า (`minutely_15`) ได้
- รองรับโหมดจำลองสถานการณ์ `mock_state` (`rain`, `clear`, `error`)

### 2. API Accuracy Evaluation Model
- เพิ่ม Model `ApiReliability` สำหรับเก็บสถิติความแม่นยำ (total_queries, false_alarms)
- เพิ่มฟีเจอร์ปุ่มกด "❌ แจ้งเตือนผิดพลาด (False Alarm)" ใน Telegram ซึ่งจะลดคะแนนความแม่นยำของ API
- อัปเดต `/api/v1/weather/compare` ให้แสดงผล % ความแม่นยำบนหน้า Telegram

### 3. การผนวกเข้ากับ WeatherManager
- **ไฟล์:** `backend/app/services/weather_manager.py`
- **Fallback Contingency**: หาก Xweather แจ้งเตือนล้มเหลว จะสลับไปดึงข้อมูลทิศทางลมจาก Open-Meteo ทันที
- **Auto-Select Order**: `predict_rain` จะดึงคะแนน Accuracy เพื่อคัดกรองจัดเรียง Fallback (เช่น หาก Tomorrow.io มีคะแนนสูงกว่า จะถูกเรียกใช้งานก่อน)

### 4. การทดสอบ (Verification & Testing)
- **ไฟล์:** `backend/tests/test_open_meteo.py`, `test_db.py`, `test_firestore.py`, `test_webhook.py`
- ตรวจสอบและเพิ่มเติม Unit Test/E2E Test แบบ TDD ทุกระบบ
- เพิ่ม [manual_verification.md](file:///Users/oatrice/Software-projects/FonMaYang/docs/features/18_issue-48-49_contingency-implement-manual-wind-vector-trajectory-ope-9d29354d/manual_verification.md) เพื่อเป็นคู่มือทดสอบ E2E สลับ API ด้วยตัวเอง
- รัน `pytest` ผ่านทั้งหมดเรียบร้อย ไม่มีข้อผิดพลาด
