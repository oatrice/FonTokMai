# 🚀 Walkthrough: Adapter Pattern สำหรับฐานข้อมูลและระบบตั้งเวลา

เราได้ทำการ Refactor โค้ดของ **FonMaYang** ให้รองรับการนำขึ้น Production บน Firebase (Firestore + Cloud Scheduler) โดยยังคงรักษาโค้ดเดิมที่ใช้ SQLite + APScheduler ให้สามารถทำงานได้เหมือนเดิมผ่านการเปลี่ยน Environment Variable ครับ

## 1. แยก ฐานข้อมูล (Repository Pattern)

เราได้สร้าง Interface ตรงกลางที่ชื่อว่า `LocationRepository` และมี Implementation 2 ตัว:
- **`SQLiteLocationRepository`**: สำหรับเซิร์ฟเวอร์ส่วนตัว หรือ Local
- **`FirestoreLocationRepository`**: สำหรับรันบน Firebase Cloud Functions (หรือ App Hosting) โดยใช้ `firebase-admin`

ในส่วนของการฉีด Dependency (DI) เราได้ใช้ `get_repo_context()` ใน `app.dependencies` เพื่อสลับการทำงานตามตัวแปร `STORAGE_BACKEND`:
```python
@asynccontextmanager
async def get_repo_context() -> AsyncGenerator[LocationRepository, None]:
    backend = os.getenv("STORAGE_BACKEND", "sqlite").lower()
    if backend == "firestore":
        yield get_firestore_repo()
    else:
        async with AsyncSessionLocal() as session:
            yield SQLiteLocationRepository(session)
```

## 2. แยกระบบตั้งเวลา (Scheduler Pattern)

เนื่องจาก Firebase ไม่สามารถรัน APScheduler ไว้ตลอดเวลาได้ เราจึงแยกระบบออกเป็น 2 โหมดควบคุมผ่าน `SCHEDULER_TYPE`:
- **โหมด `apscheduler`** (ค่าเริ่มต้น): `main.py` จะผูก APScheduler เข้ากับ Lifespan ของ FastAPI เหมือนเดิม
- **โหมด `external`**: ไม่มีการรัน APScheduler แต่เราได้เปิด Endpoint ไว้ที่ `POST /api/v1/internal/trigger-rain-check` โดย Endpoint นี้ต้องส่ง Header `X-Cron-Secret` มาด้วย เพื่อให้ Google Cloud Scheduler ยิง Request เข้ามาทุก 5 นาทีอย่างปลอดภัย

## 3. ผลลัพธ์จากการทดสอบ (TDD)
- ทำการลบไฟล์ `services/location.py` เดิมทิ้ง และแทนที่ด้วย Dependency Injection ใน `webhook.py` และ `scheduler_tasks.py` อย่างสมบูรณ์
- ระบบ Test ทั้ง 17 ตัวผ่านทั้งหมด (ครอบคลุมทั้ง API, DB, Repository Interface, Scheduler และ Webhook)

## 4. โครงสร้างพื้นฐานบน Firebase และอัปเดตระบบแจ้งเตือน (ล่าสุด)
- ปรับแก้ `firebase.json` ให้ชี้ไปที่โฟลเดอร์ `backend/` แทนการแยกโปรเจกต์
- สร้างไฟล์ `backend/main.py` ทำหน้าที่เป็น HTTPS Function ห่อหุ้ม FastAPI 
- อัปเดต `backend/requirements.txt` ให้รองรับ `firebase-admin` และ `firebase-functions` เพื่อเตรียมพร้อมขึ้น Cloud
- ปรับเปลี่ยนฟีเจอร์พยากรณ์ฝน (`RainbowService`) ให้รองรับการอ่าน API Key ผ่าน `.env` (ตัวแปร `RAINBOW_API_KEY`)
- เพิ่มลิงก์ **Zoom Earth Radar** อัตโนมัติท้ายข้อความแจ้งเตือน เพื่อให้ผู้ใช้กดเข้าไปตรวจสอบเรดาร์เมฆฝนได้ทันที
- สร้าง GitLab Issue #11 เพื่อเตรียมเปลี่ยน Placeholder API เป็นข้อมูลสภาพอากาศจริงจาก Tomorrow.io หรือ OpenWeatherMap ในอนาคต
