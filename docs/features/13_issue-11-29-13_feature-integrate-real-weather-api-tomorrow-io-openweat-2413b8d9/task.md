# งานอัปเดตระบบพยากรณ์อากาศ (Tomorrow.io + Fallback)

- [x] `backend/.env.example` เพิ่มตัวแปร `TOMORROW_API_KEY` และ `RAIN_TRIGGER_THRESHOLD_MM`
- [x] สร้าง `backend/app/services/tomorrow.py`
  - [x] ดึง Timelines API รายนาที
  - [x] ดึงฟิลด์ `precipitationIntensity`, `windSpeed`, `windDirection`
- [x] ปรับปรุง `backend/app/services/rainbow.py`
  - [x] ปรับปรุงให้รองรับการถูกเรียกผ่าน Manager (แยก Local/Global)
- [x] สร้าง `backend/app/services/weather_manager.py`
  - [x] จัดการ Fallback: Tomorrow.io -> Rainbow Local -> Rainbow Global
- [x] อัปเดต `backend/app/scheduler_tasks.py`
  - [x] ใช้ `WeatherManager` แทน `RainbowService` โดยตรง
  - [x] ตรวจสอบ `RAIN_TRIGGER_THRESHOLD_MM`
  - [x] คำนวณเวลาตก (HH:mm) และระยะห่างของฝน
  - [x] ฟอร์แมตข้อความ Telegram ใหม่ตามแผน
- [x] ทดสอบระบบ (Unit tests และ Manual test)
