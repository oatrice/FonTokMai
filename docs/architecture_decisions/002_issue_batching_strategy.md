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

เพื่อความปลอดภัยในการทำ Code Review และการส่งมอบฟีเจอร์อย่างต่อเนื่อง ได้มีการปรับปรุง Batch การทำงานใหม่ (อัปเดต มิ.ย. 2026) โดยเพิ่มกลุ่มงาน Xweather และ UX เข้ามา:

### ✅ Batch A & B: Core, DevOps & Database (Completed)
* **ขอบเขตงาน:** 
  - #15 (CI/CD) 
  - #11, #29, #13 (Integrate Tomorrow.io / Extended Data)
  - #9 (Multiple Locations - Refactored Schema)
* **สถานะ:** เสร็จสมบูรณ์ ระบบสามารถรับหลายพิกัดต่อ 1 User (ผ่านคอลัมน์ name ในตาราง) และแจ้งเตือนพร้อมข้อมูลปริมาณฝนได้อย่างเสถียร

### 📦 Batch D: UX, Bot Reliability & Tech Debt (แนะนำให้ทำทันที)
*(Quick Wins สามารถแยกทำ MR เล็กๆ ได้)*
* **ขอบเขตงาน:** 
  - #38 (Tech Debt: Refactor Webhook to use WeatherManager) **[ด่วนที่สุด]**
  - #37 (Immediate Reply/Loading State)
  - #26 (Smart Cooldown Escalation)
* **ความคาดหวัง:** ล้างหนี้ทางเทคนิคให้ Webhook กลับมาใช้ Fallback ที่ถูกต้อง, ยกระดับประสบการณ์ผู้ใช้ (UX) ให้ตอบสนองทันที และเพิ่มความฉลาดให้ระบบ Cooldown

### 📦 Batch E: Xweather Integration & Advanced Alerts (แนะนำให้ทำถัดไป)
*(ควรแยก MR ทีละฟีเจอร์)*
* **ขอบเขตงาน:** 
  - #32 (Integrate Xweather API)
  - #33 (Severe Weather & Flood Alerts)
  - #34 (Lightning Proximity Alerts)
  - #35 (Storm Cell Tracking & ETA)
* **ความคาดหวัง:** วางระบบเชื่อมต่อกับ Xweather และขยายความสามารถในการเตือนภัยพิบัติและฟ้าผ่าแบบ Hyper-local ซึ่งเป็นการยกระดับความสามารถของบอทให้เหนือกว่าการแจ้งเตือนฝนปกติ

### 📦 Batch F: Interactive Telegram Mini App
*(ทำหลังจาก Batch E เสถียรแล้ว)*
* **ขอบเขตงาน:** #36 (Live Weather Map Mini App)
* **ความคาดหวัง:** มีแผนที่แบบ Vector เรดาร์ฝนที่ลื่นไหลให้ผู้ใช้กดดูได้โดยไม่ต้องออกจากแอป Telegram

### 📦 Batch G: Crowdsourcing & AI Training (Research & Future Scope)
*(ทำหลังจากฟีเจอร์หลักเริ่มนิ่งแล้ว)*
* **ขอบเขตงาน:** 
  - #39 (Interactive Ground Truth Feedback)
  - #40 (AI Training via Radar/JSON Uploads)
* **ความคาดหวัง:** รวบรวมข้อมูลสภาพอากาศจริงจากผู้ใช้ (Ground Truth) และสร้างช่องทางสำหรับป้อนข้อมูลให้ AI เรียนรู้ เพื่อแก้ปัญหาโมเดลผิดพลาด (เช่น Virga) ในระยะยาว

### 📦 Batch C: Spatial Architecture (Pending)
*(ต้องแยกทำ 1 MR เดี่ยวๆ)*
* **ขอบเขตงาน:** #7 (Geofencing)
* **ความคาดหวัง:** เปลี่ยนแปลงวิธีคิดของระบบ Scheduler ครั้งใหญ่จาก 1-to-1 เป็น Zone-to-Many
