# ADR 001: Development Sequence and Task Scheduler Strategy

## Status
Accepted

## Context
เอกสารฉบับนี้สรุป Tradeoffs ของแนวทางการพัฒนา (Development Sequence) และการเลือกใช้ Task Scheduler สำหรับโปรเจกต์ **FonMaYang (RainNowcast)**

## Decisions

### 1. Development Sequence (Chain of Issues)
เราได้เลือกแนวทางการพัฒนาแบบ **End-to-End Core (API -> Notification -> Cron Job)** 
- เริ่มจากสร้าง API รับพิกัดแบบ On-demand 
- เชื่อมต่อ Notification ส่งกลับให้ผู้ใช้ทาง Telegram
- ครอบด้วยระบบ Automation (Cron Job) ตามมา
*เหตุผล:* ทำให้สามารถทดสอบ Business Logic ทั้งหมดแบบ On-demand ได้ทันที และเห็นผลลัพธ์เป็นรูปธรรมเร็วที่สุด

### 2. Task Queue / Scheduler
เราได้เลือกใช้ **APScheduler (รันร่วมกับ FastAPI)** แทนที่จะใช้ Celery + Redis ในระยะเริ่มต้น
- **APScheduler:** ฝัง (Embed) ตัว Scheduler รันอยู่ใน Process เดียวกับ FastAPI ได้เลย เบา (Lightweight) เหมาะกับงานที่เป็นแค่ Cron Job ดึงข้อมูลตามรอบเวลา
- *ข้อจำกัดที่ยอมรับได้:* ถ้ามีการ Scale FastAPI หลาย instance จะต้องทำ Distributed Lock ผ่าน Redis ในอนาคต

## Consequences
- **Positive:** สามารถเริ่มโปรเจกต์แบบ MVP ได้อย่างรวดเร็ว โครงสร้างไม่ซับซ้อนเกินความจำเป็น
- **Negative:** ขาดระบบ Retry และ Queue ที่แข็งแกร่งแบบ Celery ในระยะสั้น
