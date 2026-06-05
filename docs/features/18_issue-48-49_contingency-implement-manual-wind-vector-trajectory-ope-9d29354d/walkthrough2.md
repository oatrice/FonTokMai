# Walkthrough: Open-Meteo Integration

ตามที่มีการมอบหมายให้ผนวก **Open-Meteo** เข้ากับระบบ `WeatherManager` ของโปรเจกต์ FonMaYang งานทั้งหมดได้ดำเนินการเสร็จสิ้นเรียบร้อย โดยได้อ้างอิงและรองรับเป้าหมายตาม Issue ของระบบ:
- **Issue #48:** Contingency plan สำหรับการคำนวณทิศทางพายุ (Wind Vector Trajectory) กรณีที่ Xweather ล้มเหลว
- **Issue #49:** เพิ่มเข้าไปใน `compare_all_apis` เพื่อประเมินความแม่นยำเทียบกับผู้ให้บริการอื่นๆ

## 🚀 สิ่งที่พัฒนาขึ้น (Changes Made)

### 1. บริการ Open-Meteo (OpenMeteoService)
## สรุปงานที่ทำ
ในส่วนนี้ได้ดำเนินการพัฒนาระบบ Contingency Fallback Order สำหรับ Issue #48 และได้เพิ่มเติมการทำ Evaluation API Accuracy (Issue #49) ดังนี้:

- **Contingency System**: สลับ API ให้อัตโนมัติในกรณีที่ Xweather หยุดทำงาน โดยเรียงไป Tomorrow.io -> Rainbow Local -> Rainbow Global
- **Advanced Alerts Fallback**: หาก Xweather แจ้งเตือนล้มเหลว จะสลับไปดึงข้อมูลทิศทางลมและความเร็วลมแบบ Real-time จาก Open-Meteo แทน เพื่อใช้ประเมินทิศทางพายุ
- **API Accuracy Evaluation Model (Issue #49)**:
  - เพิ่ม Model `ApiReliability` สำหรับเก็บสถิติความแม่นยำรายวัน / สะสม
  - เพิ่มปุ่มกด False Alarm ใน Telegram ซึ่งจะบวกค่าความผิดพลาดลงไปที่ API source ที่กำลังใช้งาน
  - อัปเดต `WeatherManager` ให้คัดกรอง (Sort) Fallback ตาม Accuracy Score ก่อนเรียกข้อมูลเสมอ เพื่อผลลัพธ์ที่แม่นยำที่สุด
  - อัปเดต `/api/v1/weather/compare` ให้แสดงผล % ความแม่นยำบน Telegram
- **E2E Manual Verification**: เพิ่ม Test case เกี่ยวกับระบบแจ้งเตือน, การสลับ API, การจำลองสถานการณ์ (`/devmock`) และดูคะแนน Evaluation ใน [manual_verification.md](file:///Users/oatrice/Software-projects/FonMaYang/docs/features/18_issue-48-49_contingency-implement-manual-wind-vector-trajectory-ope-9d29354d/manual_verification.md)_rain_by_location`, `get_wind_vector`, และระบบสลับโมเดลอัตโนมัติ

### 2. การผนวกเข้ากับ WeatherManager
- **ไฟล์:** `backend/app/services/weather_manager.py`
- เพิ่มเป็น **Fallback Contingency** ภายใน `get_advanced_alerts`: หาก Xweather ระบบล่ม ระบบจะสลับไปดึงทิศทางลม (`direction_cardinal`) จาก Open-Meteo แทน เพื่อไม่ให้เสียข้อมูลการคำนวณพายุแบบสมบูรณ์
- เพิ่มเข้าไปใน `compare_all_apis` เพื่อให้สามารถดึงข้อมูลขนานกับ API อื่นๆ เอามาตรวจสอบและเปรียบเทียบในอนาคต

### 3. การทดสอบ (Verification & Testing)
- **ไฟล์:** `backend/tests/test_open_meteo.py`
- เขียน Unit Test ทั้งหมดด้วยกระบวนการ **TDD (Red -> Green -> Refactor)**
- ตรวจสอบ `predict_rain_by_location`, `get_wind_vector`, และระบบสลับโมเดลอัตโนมัติ

## ✅ ผลการทดสอบ (Validation Results)
รัน `pytest backend/tests/` ผ่าน **53 รายการ** 100% ไม่มีข้อผิดพลาดที่กระทบกับการทำงานหลักของ Service เดิม และมั่นใจได้ว่า Flow ใหม่ไม่รบกวนระบบเก่า

## 🔗 Next Steps
- (Issue #48) รอเขียนโค้ดต่อยอดสำหรับสมการการเคลื่อนตัวของเซลล์ฝน (Advection Equation) จากข้อมูล Wind Vector
- (Issue #49) เริ่มทำ Dashboard เปรียบเทียบข้อมูลที่ดึงมาจริงในสภาวะที่มีฝนตก
