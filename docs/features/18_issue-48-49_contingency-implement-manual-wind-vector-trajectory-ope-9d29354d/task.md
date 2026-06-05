# Tasks: Open-Meteo Integration

- `[x]` เขียน Unit Test (Failing Test) สำหรับ `OpenMeteoService` (`backend/tests/test_open_meteo.py`)
- `[x]` พัฒนา `OpenMeteoService` (Passing Code) สำหรับ `predict_rain_by_location` และ `get_wind_vector`
- `[x]` รวม `OpenMeteoService` เข้าไปใน `WeatherManager.__init__` และ `compare_all_apis`
- `[x]` ผนวก `OpenMeteoService.get_wind_vector` เข้าไปเป็น Fallback (Contingency) เมื่อ Xweather ล้มเหลวใน `get_advanced_alerts`
- `[x]` อัปเดต Mock Router สำหรับ `OpenMeteo` ในระบบทดสอบ (`backend/mock_emsc_ws.py` หรือสร้างไฟล์ mock ใหม่)
- `[x]` ตรวจสอบและ Refactor โค้ดให้ผ่านการทดสอบทั้งหมด (TDD: Red -> Green -> Refactor)
- `[x]` แจ้งเตือนปิดงานด้วย `notify_task_complete`
