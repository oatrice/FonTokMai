# Architecture & Development Tradeoffs

เอกสารฉบับนี้สรุป Tradeoffs ของแนวทางการพัฒนา (Chain of Issues / Development Sequence) และการเลือกใช้ Task Scheduler สำหรับโปรเจกต์ **FonMaYang (RainNowcast)**

---

## 1. Tradeoffs ของลำดับการพัฒนา (Development Sequence / Chain of Issues)

การเลือกชิ้นงานที่จะพัฒนาก่อน-หลัง มีผลต่อการทดสอบและการส่งมอบฟีเจอร์ แบ่งเป็น 3 แนวทางหลัก:

### แบบที่ 1: Data First (Cron Job $\rightarrow$ API $\rightarrow$ Notification)
เริ่มจากระบบดึงข้อมูลอัตโนมัติ (Background Tasks) ก่อน
- **ข้อดี:** ได้ทดสอบความเสถียรของการเชื่อมต่อกับ 3rd-party Weather APIs (RainViewer, Rainbow) แบบต่อเนื่องแต่เนิ่นๆ ว่ามีปัญหา Rate Limit หรือไม่ ทำให้มีข้อมูลจริงพร้อมใช้
- **ข้อเสีย:** มองไม่เห็นภาพรวมของฝั่งผู้ใช้จนกว่าจะทำ API หรือ Notification เสร็จ

### แบบที่ 2: End-to-End Core (API $\rightarrow$ Notification $\rightarrow$ Cron Job)
เริ่มจากสร้าง API รับพิกัดแบบ On-demand $\rightarrow$ เชื่อมต่อ Notification ส่งกลับให้ผู้ใช้ $\rightarrow$ ทำระบบอัตโนมัติ (Cron) ตามมา
- **ข้อดี:** สามารถทดสอบ Business Logic ทั้งหมดแบบ On-demand ผ่าน Postman หรือ Swagger UI ได้ทันที (ส่งแจ้งเตือนเข้า Line/Telegram ได้จริง) ทำให้เห็นผลลัพธ์เป็นรูปธรรมเร็วที่สุด
- **ข้อเสีย:** ระบบยังไม่ Automation เต็มตัวในช่วงแรก ต้องกดเรียก API เอง

### แบบที่ 3: User Interface First (Notification $\rightarrow$ API $\rightarrow$ Cron Job)
เริ่มทำระบบ Line OA / Telegram Bot Webhook ก่อน เพื่อรับคำสั่งจากผู้ใช้
- **ข้อดี:** ผู้ใช้ (Tester) สามารถเริ่มคุยกับ Bot ได้ทันที ใช้เวลา Setup การเชื่อมต่อแพลตฟอร์มนอกได้เสร็จไว
- **ข้อเสีย:** ถ้า Core Logic ยังไม่เสร็จ Bot จะตอบสนองได้แค่ Mock data

> **🌟 คำแนะนำ (Recommendation):** เลือก **แบบที่ 2 (End-to-End Core)** โดยทำ API Routers ให้เรียก Service ที่มีอยู่แล้วส่ง Notification ออกไป เมื่อวงจรนี้สมบูรณ์ จึงครอบด้วยระบบ Automation (Cron Job) 

---

## 2. Tradeoffs ของ Task Queue / Scheduler (Celery vs APScheduler)

สำหรับการดึงข้อมูลฝนทุกๆ 5-10 นาที (Cron Job)

### ตัวเลือก A: Celery + Redis
เครื่องมือมาตรฐานระดับอุตสาหกรรมสำหรับการจัดการ Background Tasks 
- **ข้อดี:**
  - Robust และ Scale ได้ดีมาก ถ้าระบบขยายตัวสามารถเพิ่ม Worker node ได้ง่าย
  - มีระบบ Retry, Error Handling, และ Task Chaining/Routing ที่ครบถ้วน
  - แยก Process ออกจาก FastAPI ชัดเจน (API ไม่พังถ้า Cron Job มีปัญหา)
- **ข้อเสีย:**
  - Setup ค่อนข้างซับซ้อน ต้องรันอย่างน้อย 3 processes (FastAPI, Celery Worker, Celery Beat)
  - ซดทรัพยากรมากกว่า เหมาะกับโปรเจกต์ที่สเกลใหญ่

### ตัวเลือก B: APScheduler (รันร่วมกับ FastAPI) + Redis (Optional)
Library ยอดนิยมสำหรับตั้งเวลาการทำงานของ Python
- **ข้อดี:**
  - Setup ง่ายมาก สามารถฝัง (Embed) ตัว Scheduler รันอยู่ใน Process เดียวกับ FastAPI ได้เลย (ไม่ต้องมี Worker แยก)
  - เบา (Lightweight) เหมาะกับงานที่เป็นแค่ Cron Job ดึงข้อมูลตามรอบเวลา
- **ข้อเสีย:**
  - ถ้ามีการ Scale FastAPI หลาย instance (เช่น Uvicorn workers หลายตัว หรือรันหลาย Pods) ตัว Cron จะถูกรันซ้ำตามจำนวน instance เว้นแต่จะใช้ Redis + Distributed Lock (เช่น `RedisJobStore` หรือทำ Mutex lock)
  - หาก Task ทำงานหนัก อาจไปเบียดบังทรัพยากรการตอบสนอง HTTP request ของ FastAPI ได้

> **🌟 คำแนะนำ (Recommendation):** 
> - หากต้องการ **เริ่มให้เร็วและระบบยังเล็ก (MVP):** ใช้ **APScheduler** (ทำ Distributed Lock ผ่าน Redis)
> - หากกังวลเรื่อง **Scalability อนาคต** หรือต้องการทำ Notification Queue แบบจริงจังแยกจาก Cron: ใช้ **Celery + Redis** ไปเลยตั้งแต่แรก จะตอบโจทย์ Pluggable Design ในระยะยาวได้ดีกว่า
