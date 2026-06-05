# Tasks: Open-Meteo & API Evaluation (Issue 48 & 49)

## Issue #48: Open-Meteo Contingency
- `[x]` เขียน Unit Test (Failing Test) สำหรับ `OpenMeteoService`
- `[x]` พัฒนา `OpenMeteoService` สำหรับ `predict_rain_by_location` และ `get_wind_vector`
- `[x]` รวม `OpenMeteoService` เข้าไปใน `compare_all_apis`
- `[x]` ผนวก `OpenMeteoService.get_wind_vector` เข้าไปเป็น Fallback (Contingency) เมื่อ Xweather ล้มเหลว

## Issue #49: API Accuracy Evaluation
- `[x]` **1. Database Model**: สร้าง `ApiReliability` model และ migration
- `[x]` **2. Repository Pattern**: Implement `get_all_api_reliability` และ `save_feedback` ใน SQLite และ Firestore
- `[x]` **3. WeatherManager**: เรียง Fallback Order ตามคะแนน Accuracy และเพิ่มฟีเจอร์นับ Query
- `[x]` **4. Compare API**: แสดง % ความแม่นยำบนเมนู "📊 เทียบข้อมูล" ใน Telegram
- `[x]` **5. Documentation & Verification**: เขียน E2E คู่มือทดสอบ และ Automated Tests
