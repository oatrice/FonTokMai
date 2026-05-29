# แผนการ Refactor เป็น Adapter Pattern สำหรับ Firebase และ SQLite (Issue #10)

เพื่อรองรับ **ทางเลือกที่ 2 (Firebase)** ตามที่คุณต้องการ โดยยังคงรักษา **Codebase เดิม (SQLite + APScheduler)** เอาไว้ไม่ให้พัง เราจะนำ **Adapter Pattern (Repository Pattern)** มาใช้ ซึ่งจะช่วยให้คุณสามารถสลับการทำงานระหว่างระบบเก่ากับระบบใหม่ได้เพียงแค่เปลี่ยน Environment Variable (`STORAGE_BACKEND` และ `SCHEDULER_TYPE`)

## Proposed Changes

### 1. Database Adapter (Repository Pattern)
เราจะสร้าง Interface ตรงกลางสำหรับการจัดการข้อมูล (เช่น การบันทึก/อ่าน Location)

#### [NEW] [backend/app/repositories/base.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/repositories/base.py)
- สร้าง Abstract Base Class `LocationRepository` เพื่อกำหนด method มาตรฐาน เช่น `get_location`, `save_location`, `get_active_locations`, `update_last_alerted`

#### [NEW] [backend/app/repositories/sqlite.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/repositories/sqlite.py)
- ย้ายลอจิกจาก `app/services/location.py` ที่ใช้ `AsyncSession` และ SQLAlchemy มาไว้ที่นี่

#### [NEW] [backend/app/repositories/firestore.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/repositories/firestore.py)
- สร้าง Implementation ใหม่ที่ใช้ `firebase-admin` เพื่อต่อกับ Cloud Firestore

### 2. Dependency Injection
เราจะใช้ FastAPI `Depends` เพื่อฉีด Repository ที่ถูกต้องเข้าไปใน Controller (Routers)

#### [NEW] [backend/app/dependencies.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/dependencies.py)
- ฟังก์ชัน `get_location_repo()` ที่จะตรวจสอบตัวแปร `STORAGE_BACKEND` 
  - หากเป็น `sqlite` ให้คืนค่า `SQLiteRepository`
  - หากเป็น `firestore` ให้คืนค่า `FirestoreRepository`

#### [MODIFY] [backend/app/routers/webhook.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/routers/webhook.py)
- เลิกใช้ `AsyncSessionLocal` โดยตรง และเปลี่ยนไปเรียกใช้ `repo = get_location_repo()` แทน

### 3. Scheduler Separation
แยกการทำงานของระบบตั้งเวลาแจ้งเตือนฝน

#### [MODIFY] [backend/app/main.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/main.py)
- ตรวจสอบ `SCHEDULER_TYPE` ใน lifespan
- ถ้าเป็น `apscheduler`: ให้รัน Background task แบบเดิม
- ถ้าเป็น `external` (เช่น Firebase Cloud Scheduler): จะไม่เปิด APScheduler เลย

#### [NEW] [backend/app/routers/scheduler.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/routers/scheduler.py)
- สร้าง Endpoint ใหม่ `POST /api/v1/internal/trigger-rain-check` พร้อมระบบ Authentication แบบ Secret Key
- เพื่อรองรับให้ Cloud Scheduler (ของ Firebase/GCP) ยิง Request เข้ามาเพื่อสั่งงานแทน APScheduler

## ⚠️ User Review Required

> [!IMPORTANT]  
> แผนนี้จะทำให้ระบบรองรับทั้ง **SQLite + APScheduler** (สำหรับ Local/VPS) และ **Firestore + Endpoint** (สำหรับ Firebase/GCP) ได้พร้อมกันในโปรเจกต์เดียว โดยใช้ Design Pattern อย่างสวยงาม
> 
> **ขั้นตอนการทำงานต่อไป (หากคุณอนุมัติ):**
> 1. (TDD) เขียน Test สำหรับ Repository Interface เพื่อรองรับ Adapter
> 2. Implement ตัว Repository 
> 3. แก้ไข Webhook และ Scheduler
> 4. แนะนำวิธีตั้งค่า Firebase และ Cloudflare Tunnels (สำหรับ Local Dev)

หากคุณเห็นด้วยกับแผนการออกแบบ (Architecture Design) นี้ รบกวนพิมพ์ **"ตกลง"** หรือคอมเมนต์เพิ่มเติมได้เลยครับ
