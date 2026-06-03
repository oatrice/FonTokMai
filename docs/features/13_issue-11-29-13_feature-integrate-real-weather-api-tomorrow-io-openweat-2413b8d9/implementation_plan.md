# การเปลี่ยน Engine แจ้งเตือนฝนเป็น Tomorrow.io (Issues #11, #29, #13)

เป้าหมายคือการแก้ปัญหา False Positive (Issue #27) อย่างเด็ดขาด ด้วยการเปลี่ยนจาก API ที่ใช้ Global Model ไปเป็น Tomorrow.io Timelines API ซึ่งมีความแม่นยำระดับพิกัด (Hyper-local) และสามารถพยากรณ์ล่วงหน้าระดับนาทีได้อย่างแม่นยำ โดยไม่ต้องคำนวณเวกเตอร์เอง

## User Review Required

> [!IMPORTANT]
> ระบบใหม่ต้องการ **Tomorrow.io API Key** ในการทำงาน รบกวนผู้ใช้นำ API Key ไปใส่ในไฟล์ `.env` ด้วยตัวแปร `TOMORROW_API_KEY` ก่อนที่เราจะเริ่มทดสอบรันระบบจริงครับ (Free Tier ให้โควต้า 500 requests/วัน)

## Proposed Changes

---

### 1. Integrate Tomorrow.io Engine (Issue #11)

#### [NEW] `backend/app/services/tomorrow.py`
- สร้างคลาส `TomorrowService` สืบทอดจาก `BaseWeatherService`
- เขียนฟังก์ชัน `predict_rain_by_location(lat, lng)` เพื่อดึงข้อมูล `Timelines API` แบบ `1m` (รายนาทีล่วงหน้า 1 ชั่วโมง)
- ดึงฟิลด์ข้อมูลที่จำเป็น: `precipitationIntensity`, `windSpeed`, `windDirection`
- เขียน Logic แปลง Time series ให้เป็น Format กลางของเรา (`predictions`, `intensity`, `duration_minutes`)

---

### 2. API Fallback Manager

#### [NEW] `backend/app/services/weather_manager.py`
- จัดการ Workflow การดึง API แบบไล่ลำดับ (Fallback):
  1. `Tomorrow.io` (Primary)
  2. `Rainbow.ai (Local)` (Secondary)
  3. `Rainbow.ai (Global)` (Fallback สุดท้าย)
- แนบข้อมูล "Data Source" กลับไปให้ Scheduler ด้วย

---

### 3. Raise Rain Alert Threshold (Issue #29)

#### [MODIFY] [backend/app/scheduler_tasks.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/scheduler_tasks.py)
- ดึงค่า `RAIN_TRIGGER_THRESHOLD_MM` จาก Environment (Default = 0.5)
- กรอง (Filter) การแจ้งเตือน: หาก `precipitationIntensity` สูงสุดของช่วงเวลานั้น < 0.5 mm/hr ให้ถือเป็น **สัญญาณรบกวน (Noise)** และข้ามการแจ้งเตือนไป

#### [MODIFY] [backend/.env.example](file:///Users/oatrice/Software-projects/FonMaYang/backend/.env.example)
- เพิ่ม `TOMORROW_API_KEY=`
- เพิ่ม `RAIN_TRIGGER_THRESHOLD_MM=0.5`

---

### 4. Enhance Alert Message (Issue #13)

#### [MODIFY] [backend/app/scheduler_tasks.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/scheduler_tasks.py)
- อัปเกรดข้อความ Telegram โดยระบุทั้งเวลาแบบ `HH:mm` และแบบ "อีกกี่นาที"
- แสดง Data Source ว่ามาจากไหน
- ประเมินระยะห่างของฝนจาก `ความเร็วลม × เวลา`
- ตัวอย่างข้อความใหม่:
  ```text
  🌧️ ฝนกำลังเคลื่อนมาทางพิกัดของคุณ
  ⏰ จะเริ่มตกเวลา: 17:30 น. (ในอีก 15 นาที)
  🛑 คาดว่าจะหยุดเวลา: 18:15 น. (ตกต่อเนื่อง 45 นาที)

  💧 ความรุนแรง: ปานกลาง (3.2 mm/hr)
  🌬️ สภาพลม: 20 km/h
  📏 ระยะห่างจากกลุ่มฝน: ประมาณ 5.0 กม.
  📡 แหล่งข้อมูล: Tomorrow.io
  ```

## Verification Plan

### Automated Tests
- สร้างไฟล์ทดสอบ `backend/tests/test_tomorrow.py` และ `test_weather_manager.py`
- จำลองการล่มของ Tomorrow.io เพื่อดูว่าระบบสลับไปหา Rainbow Local/Global ถูกต้อง
- ทดสอบการคำนวณเวลาและระยะห่าง
