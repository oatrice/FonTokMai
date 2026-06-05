# Task: Implement API Accuracy Evaluation (Issue 49)

- `[x]` **1. Database Model**
  - `[x]` สร้าง `ApiReliability` model ใน `app/models.py`
  - `[x]` สร้างและรัน Alembic Migration สำหรับตารางใหม่ (ใช้ Base.metadata.create_all ตอน server เริ่ม)
- `[x]` **2. Repository Pattern**
  - `[x]` เพิ่ม interface สำหรับจัดการ `ApiReliability` ใน `base.py`
  - `[x]` Implement repository pattern สำหรับ SQLite (`sqlite.py`) (รวมถึง Default scores)
  - `[x]` ปรับปรุง `save_feedback` ให้ไปบวกค่า `false_alarms` ใน `ApiReliability`
- `[x]` **3. WeatherManager (Auto-Select)**
  - `[x]` ดึงค่า Reliability ก่อนทำการดึงข้อมูลพยากรณ์
  - `[x]` จัดเรียง Fallback Order ตาม Accuracy Score ที่สูงที่สุด
  - `[x]` อัปเดต `total_queries` +1 หากเรียกใช้บริการนั้นสำเร็จและทายว่ามีฝน (Max Rain > 0)
- `[x]` **4. Compare API (Telegram)**
  - `[x]` ปรับปรุง `/api/v1/weather/compare` ให้คืนค่า Accuracy Score ออกมาด้วย
  - `[x]` แสดงผล Accuracy Score บนปุ่ม 📊 เทียบข้อมูล ใน Telegram
- `[x]` **5. Documentation & Verification**
  - `[x]` ปรับปรุงคู่มือการทดสอบ (E2E) ให้ครอบคลุมฟีเจอร์นี้
  - `[x]` Verify E2E Flow (Tests)
