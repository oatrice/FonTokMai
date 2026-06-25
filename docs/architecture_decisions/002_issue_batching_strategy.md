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

### ✅ Batch D: UX, Bot Reliability & Tech Debt (Completed)
* **ขอบเขตงาน:** 
  - #38 (Tech Debt: Refactor Webhook to use WeatherManager)
  - #37 (Immediate Reply/Loading State)
  - #26 (Smart Cooldown Escalation)
* **สถานะ:** เสร็จสมบูรณ์ ล้างหนี้ทางเทคนิคให้ Webhook ผูกกับ Fallback Chain ที่ถูกต้อง, ยกระดับ UX ให้บอทตอบสนองทันที (ไม่ติด Timeout) และระบบ Smart Cooldown สามารถเตือนทะลุบล็อกได้เมื่อความรุนแรงฝนเพิ่มขึ้น

### ✅ Batch E: UX, Insights & Crowdsourcing (Completed)
*(แก้ปัญหา False Positive และเพิ่มความโปร่งใสของข้อมูล)*
* **ขอบเขตงาน:** 
  - #41 (Cancellation / All-Clear Alert - แจ้งเตือนฝนหยุด)
  - #42 (Insights API Comparison - เทียบข้อมูลทุกค่าย)
  - #39 (Interactive Ground Truth Feedback - รายงานฝนไม่ตกจริง)
* **สถานะ:** เสร็จสมบูรณ์ ลดความสับสนจาก False Positive โดยผู้ใช้สามารถเทียบข้อมูลเรดาร์เองด้วยปุ่ม Insights, มีแจ้งเตือนเมื่อกลุ่มฝนผ่านไปแล้ว และเริ่มเก็บข้อมูล Ground Truth จากผู้ใช้จริงลง Firestore แล้ว

### ✅ Batch F: Xweather Integration & Advanced Alerts (Completed)
*(Integrated Premium Weather API with Circuit Breakers)*
* **ขอบเขตงาน:** 
  - #32 (Integrate Xweather API)
  - #33 (Severe Weather & Flood Alerts)
  - #34 (Lightning Proximity Alerts)
  - #35 (Storm Cell Tracking & ETA)
  - #31 (Wind Vector Nowcasting - Superseded by Xweather Stormcells)
  - #16 (Integrate external meteorological APIs - Superseded)
* **สถานะ:** เสร็จสมบูรณ์ นำ Xweather มาใช้แจ้งเตือนฟ้าผ่า, ทิศทางพายุ, และมีระบบ Circuit Breaker กันโควต้าเต็ม

### ✅ Batch N: TMD Radar High-Res Polling & Reliability (Completed)
*(เปลี่ยนผ่านสถาปัตยกรรม TMD Radar)*
* **ขอบเขตงาน:** 
  - #113 (Add +7 IDC overlay)
  - #114 (Radar out of date validation)
  - #115 (Migrate to Polled Static Frames)
* **สถานะ:** เสร็จสมบูรณ์ นำระบบ Polling Static Image มาใช้ร่วมกับ Smart GIF Fallback Recovery ลดการโหลด GIF ขนาดใหญ่ และเพิ่มความน่าเชื่อถือของการพยากรณ์

### 📦 Batch G: Comprehensive Weather & Air Quality
*(ฟีเจอร์พยากรณ์อากาศแบบครบวงจรประจำวัน)*
* **ขอบเขตงาน:** 
  - #44 (Feature: Batch G - Comprehensive Weather & Air Quality)
* **ความคาดหวัง:** เพิ่มระบบ `/forecast` (ล่วงหน้า 7 วัน), `/aqi` (ฝุ่น/มลพิษ) และ Cron Job สรุปอากาศยามเช้า

### 📦 Batch H: Disasters & Natural Hazards Alerts
*(ระบบความปลอดภัยขั้นสูงสุด)*
* **ขอบเขตงาน:** 
  - #45 (Feature: Batch H - Disasters & Natural Hazards Alerts)
* **ความคาดหวัง:** แจ้งเตือนแผ่นดินไหว, ไต้ฝุ่น, และจุดความร้อน/ไฟป่า ล่วงหน้าเมื่อกระทบรัศมีผู้ใช้

### 📦 Batch I: Interactive Maps & Routing (Telegram Mini App)
*(ประสบการณ์ผู้ใช้แบบกราฟิก Web-based)*
* **ขอบเขตงาน:** 
  - #46 (Feature: Batch I - Interactive Weather Maps & Routing)
  - #36 (Telegram Mini App - Live Weather Map)
  - #14 (Rain Prediction along Driving Route)
  - #28 (Switch to RainViewer Radar API for Tiles)
* **ความคาดหวัง:** ผู้ใช้สามารถกดเปิดแผนที่เรดาร์ฝนแบบโต้ตอบได้โดยไม่ต้องออกจาก Telegram และจัดเส้นทางขับรถหนีฝนได้

### 📦 Batch J: Spatial Architecture & Geofencing Optimization
*(เพิ่มความแม่นยำเชิงพื้นที่ ลด False Positive)*
* **ขอบเขตงาน:** 
  - #7 (Broad Geofencing and District-Level Alert System)
  - #30 (Tighten Geofence Radius to 5-10 km)
  - #27 (Bug: False Positive Rain Alert caused by Global Model)
* **ความคาดหวัง:** ปรับสถาปัตยกรรม Scheduler จาก 1-to-1 เป็น Zone-to-Many และจำกัดรัศมีเตือนฝนเพื่อลดการแจ้งเตือนผิดพลาดจากพายุที่อยู่ไกลออกไป

### 📦 Batch K: AI & Machine Learning Pipeline
*(นำ Data ที่รวบรวมไว้มาใช้งานจริง)*
* **ขอบเขตงาน:** 
  - #40 (Feature: AI Training via Radar Image / JSON Uploads)
* **ความคาดหวัง:** ประมวลผล Ground Truth Data ที่ User โหวตเข้ามา นำไปเทรน Machine Learning Model เพื่อ Nowcasting

### 📦 Batch L: Infrastructure & Multi-Platform (Future)
*(เตรียมตัวก้าวข้าม Telegram และยกระดับระบบเซิร์ฟเวอร์)*
* **ขอบเขตงาน:** 
  - #47 (Infrastructure: Migrate to Terraform & Google Secret Manager)
  - #8 (Develop Cross-Platform Mobile App)
  - #5 (Integrate Notification Services for Line OA)
* **ความคาดหวัง:** เปลี่ยนไปใช้ Infrastructure as Code (Terraform) ให้ระบบความปลอดภัยสูงสุด และเตรียมเชื่อมต่อแอปแยก/Line OA

---

## Post-Incident Batches (Added June 2026)
*หมวดหมู่ที่ถูกเพิ่มเข้ามาใหม่เพื่อรองรับการขยายตัวและคุมงบประมาณ*

### 📦 Batch M: Observability & FinOps
*(ดูรายละเอียดและแผนการแยก MR เชิงลึกได้ที่ `ADR 008`)*
* **ขอบเขตงาน:** 
  - #73, #74, #79, #108, #116
* **ความคาดหวัง:** ตรวจสอบสุขภาพระบบ, ดึง Metrics ของคิว, กรองแผ่นดินไหวจากต้นทาง และทำสคริปต์ซิงค์ข้อมูล Cloud Scheduler

### 📦 Batch O: Bot Intelligence & Cost Automation
*(นำระบบการควบคุมทรัพยากรและแจ้งเตือนเข้าสู่ Telegram)*
* **ขอบเขตงาน:** 
  - #80 (Route billing and system alerts to dedicated DevBot)
  - #81 (Adjust GCP Budget via Telegram command `/setbudget`)
  - #82 (Manage GCP Budget and Alerts via Terraform IaC)
* **ความคาดหวัง:** แยกการแจ้งเตือนของนักพัฒนาออกจากกลุ่มผู้ใช้ทั่วไป และสามารถสั่งลด/เพิ่มงบ GCP ได้จากปลายนิ้วผ่าน Telegram

### 📦 Batch P: Nationwide Radar Expansion & Calibration
*(ยกระดับความครอบคลุมของเรดาร์)*
* **ขอบเขตงาน:** 
  - #99 (Auto-calibration pipeline for new radar stations)
  - #52 (Expand TMD Radar integration to nationwide coverage)
  - #40 (AI Training via Radar Image / JSON Uploads)
* **ความคาดหวัง:** สร้าง Pipeline ที่ทำให้การเพิ่มสถานีเรดาร์ใหม่ๆ ของกรมอุตุฯ ทำได้อัตโนมัติ และครอบคลุมผู้ใช้งานทั่วประเทศ
