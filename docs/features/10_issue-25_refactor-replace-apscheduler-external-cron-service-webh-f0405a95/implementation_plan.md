# แผนการพัฒนา Issue #25: Replace APScheduler with external cron service and webhook endpoint

Issue นี้มีเป้าหมายเพื่อถอด `APScheduler` ออกจากแอปพลิเคชัน แล้วสร้าง API Endpoint `/api/v1/cron/check-rain` ขึ้นมาแทนที่ เพื่อให้ External Cron Service อย่างเช่น Google Cloud Scheduler หรือ cron-job.org ทำหน้าที่ยิง Request เข้ามาเพื่อรัน Background Task แทนการให้แอปพลิเคชันจัดการ Scheduling เอง ช่วยลดปัญหาเวลา deploy บน Cloud Run ที่อาจมีหลาย instances (เกิด race conditions) หรือ Cloud Run scale to zero ทำให้ cron หยุดทำงาน

## User Review Required

> [!IMPORTANT]
> - Endpoint จะถูกเปลี่ยนชื่อจาก `/api/v1/internal/trigger-rain-check` เป็น `/api/v1/cron/check-rain`
> - การ authentication ยังคงใช้ `X-Cron-Secret` header เพื่อความปลอดภัยเหมือนเดิม
> - `apscheduler` จะถูกลบออกจาก `requirements.txt` และ dependencies ที่เกี่ยวข้องทั้งหมด

## Open Questions

- รหัส HTTP Status ที่ต้องการส่งกลับหลังจากโยน task เข้า BackgroundTasks แล้ว ควรใช้ `200 OK` หรือ `202 Accepted` ดีครับ? (โดย default FastAPI จะเป็น 200 แต่เนื่องจากเราผลักภาระเข้า BackgroundTasks อาจใช้ 202 ก็ได้ แต่ในแผนนี้ผมจะคง 200 ตามเดิมไว้ก่อน)

## Proposed Changes

---

### Backend Configuration

#### [MODIFY] [main.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/main.py)
- นำโค้ดที่เรียกใช้และ initialize `apscheduler` ออกจากฟังก์ชัน `lifespan` 
- นำการดึง environment variable `SCHEDULER_TYPE` ออก

#### [MODIFY] [requirements.txt](file:///Users/oatrice/Software-projects/FonMaYang/backend/requirements.txt)
- ลบ dependency `apscheduler` ออกจากไฟล์

---

### Backend Router & Endpoints

#### [MODIFY] [scheduler.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/app/routers/scheduler.py)
- เปลี่ยน `prefix` จาก `/api/v1/internal` เป็น `/api/v1/cron`
- เปลี่ยน path จาก `/trigger-rain-check` เป็น `/check-rain` (เมื่อรวมกันจะได้เป็น `/api/v1/cron/check-rain`)

---

### Tests

#### [MODIFY] [test_scheduler.py](file:///Users/oatrice/Software-projects/FonMaYang/backend/tests/test_scheduler.py)
- เขียนเทสต์เพิ่มเติมแบบ TDD สำหรับ HTTP endpoint `/api/v1/cron/check-rain` โดยใช้ `TestClient` เพื่อตรวจสอบการตอบสนองกรณีที่ใส่ และไม่ใส่ `X-Cron-Secret` header ได้ถูกต้อง

## Verification Plan

### Automated Tests
- รัน `pytest backend/tests/test_scheduler.py` เพื่อตรวจสอบ logic ของ background task (ของเดิมที่มีอยู่แล้ว) ว่ายังทำงานได้ปกติ
- รัน `pytest` เพื่อทดสอบ endpoint ใหม่ว่ามีการจัดการ Header ได้ถูกต้อง

### Manual Verification
- รัน FastAPI server ด้วย `uvicorn` และทดสอบยิง Request เข้าไปที่ `/api/v1/cron/check-rain` ด้วย curl หรือ Postman พร้อมกับการแนบ `X-Cron-Secret` Header
