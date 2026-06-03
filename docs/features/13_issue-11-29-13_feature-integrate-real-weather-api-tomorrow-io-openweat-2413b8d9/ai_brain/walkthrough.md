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
