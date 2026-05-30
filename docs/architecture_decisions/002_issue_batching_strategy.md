# Architecture & Development Strategy: Issue Batching

## Context
จากการวิเคราะห์ความซับซ้อน (Complexity) และขนาดของการเปลี่ยนแปลง (MR Size) รวมถึงเป้าหมายของทีมที่ต้องการเน้นพัฒนาฝั่ง Telegram ให้แข็งแกร่งก่อน (และชะลอ Issue #5 Line OA ออกไป) จึงได้จัดกลุ่มการพัฒนา (Batch) ใหม่ เพื่อลดความเสี่ยงจากการเกิด Large MR และทำให้การส่งมอบฟีเจอร์มีความต่อเนื่อง

## Issue Evaluation

1. **Issue 15 (CI/CD Auto-deploy)**
   * **Complexity:** Low
   * **MR Size:** Small
   * *Detail:* วางระบบ Deploy อัตโนมัติไปยัง Google Cloud Run ผ่าน GitLab CI และใช้กลยุทธ์ "Bot 2 ตัว" เพื่อแยก Development/Production Webhook ป้องกันปัญหาตีกัน
2. **Issue 13 (Extended Meteorological Data)**
   * **Complexity:** Medium
   * **MR Size:** Medium
   * *Detail:* ปรับปรุง Logic การดึงข้อมูลสภาพอากาศเชิงลึก (เช่น ความเร็วลม, ปริมาณฝน) จาก API มาแสดงผลเพิ่มเติมในข้อความแจ้งเตือน (ไม่กระทบ Database)
3. **Issue 9 (Multiple saved locations)**
   * **Complexity:** Medium-High
   * **MR Size:** Large
   * *Detail:* แก้ไข Database Schema เพื่อรองรับความสัมพันธ์แบบ 1 User ต่อหลายสถานที่ (เช่น Home, Work) และเพิ่ม UI ให้ผู้ใช้ตั้งชื่อสถานที่ได้
4. **Issue 7 (Broad Geofencing & District-Level Alert)**
   * **Complexity:** Very High
   * **MR Size:** Very Large
   * *Detail:* รื้อโครงสร้าง Core Logic ของ Scheduler ให้ดึงพิกัดและตรวจสอบฝนตาม "โซนพื้นที่ (Geofencing)" แทนการเช็ครายบุคคล เพื่อลด API cost และประหยัดแบตเตอรี่

## Development Batches (Revised)

เพื่อความปลอดภัยในการทำ Code Review และป้องกันคอขวด ให้แบ่งการพัฒนาออกเป็น 3 ระยะ (Phases) ดังนี้:

### 📦 Batch A: DevOps & Quick Win
*(สามารถทำร่วมกันใน 1 MR ได้ หรือแยก 2 MR เล็ก)*
* **ขอบเขตงาน:** #15 (CI/CD) และ #13 (Extended Data)
* **ความคาดหวัง:** ได้ท่อ Deploy อัตโนมัติที่เสถียร และยกระดับข้อความแจ้งเตือนปัจจุบันให้มีข้อมูลครบถ้วนขึ้นทันที ถือเป็น Quick Win ที่เห็นผลเร็วที่สุด

### 📦 Batch B: Database Refactoring
*(ต้องแยกทำ 1 MR เดี่ยวๆ)*
* **ขอบเขตงาน:** #9 (Multiple Locations)
* **ความคาดหวัง:** ปรับปรุงและ Migrate Database Schema อย่างปลอดภัย งานนี้จะมีความเสี่ยงสูงต่อข้อมูลเดิม จึงต้องแยก MR เพื่อให้ Review ได้อย่างละเอียด และเป็นการปูทางไปสู่ Geofencing

### 📦 Batch C: Spatial Architecture
*(ต้องแยกทำ 1 MR เดี่ยวๆ)*
* **ขอบเขตงาน:** #7 (Geofencing)
* **ความคาดหวัง:** เปลี่ยนแปลงวิธีคิดของระบบ Scheduler ครั้งใหญ่ (Paradigm Shift) จาก 1-to-1 เป็น Zone-to-Many งานนี้ซับซ้อนที่สุดและต้องใช้เวลาทดสอบนานที่สุด
