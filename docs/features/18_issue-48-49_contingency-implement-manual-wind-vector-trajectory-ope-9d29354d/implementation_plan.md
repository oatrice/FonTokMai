# แผนการผนวก Open-Meteo & API Accuracy Evaluation

## เป้าหมาย (Goal Description)
1. **Issue #48 (Contingency):** เพิ่มบริการ Open-Meteo เพื่อดึงข้อมูลทิศทางพายุ (Wind Vector) หาก Xweather ขัดข้อง
2. **Issue #49 (Research & Evaluation):** สร้างระบบเก็บคะแนนความแม่นยำ (Accuracy Score) สำหรับแต่ละ API (เช่น Tomorrow.io, Xweather) จากระบบ Auto Select Fallback Order ตามสถิติและ Feedback ของผู้ใช้

---

## ส่วนที่ 1: Open-Meteo Contingency (Issue #48)
### Backend Services
- **`backend/app/services/open_meteo.py`**: สร้างคลาส `OpenMeteoService` พร้อมฟังก์ชัน `predict_rain_by_location` และ `get_wind_vector`
- **`backend/app/services/weather_manager.py`**:
  - ผนวก `get_wind_vector` ไว้ใน Fallback ของ `get_advanced_alerts` (หาก Xweather ล่ม)
  - เพิ่มเข้าไปในฟังก์ชัน `compare_all_apis`
- **การทดสอบ**: เขียน Unit Test ครอบคลุมการทำงานใหม่

---

## ส่วนที่ 2: API Accuracy Evaluation (Issue #49)
### Architecture
เราจะใช้ **Feedback-driven Auto Selection**:
- **`ApiReliability` Database Model**: เก็บ `total_queries`, `false_alarms`, และ `accuracy_score` ของแต่ละ API
- **Feedback Loop**: หากผู้ใช้กด ❌ แจ้งเตือนผิดพลาด (False Alarm) จาก Telegram จะหักคะแนนความแม่นยำของ API ต้นทางที่แจ้งเตือนนั้นทันที
- **Auto-Select Fallback**: `WeatherManager` จะจัดเรียงและเรียกใช้ API ตามลำดับคะแนน Accuracy ที่ได้จาก DB

---

## ส่วนที่ 3: Automated Tests สำหรับ Issue #49
- **`test_db.py` & `test_firestore.py`**: เพิ่ม Unit Test ทดสอบการอัปเดต `false_alarms` และการคำนวณ `accuracy_score`
- **`test_webhook.py`**: อัปเดตเพื่อจำลองพฤติกรรมการส่ง Payload จาก Telegram ของปุ่ม Compare และ False Alarm
