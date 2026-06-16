# Architecture Decision Record: Cost Efficiency, Billing, and Queue Batching Strategy

## Context
ในการพัฒนาโปรเจกต์ FonMaYang มีความต้องการปรับปรุงระบบในมิติของ **การควบคุมค่าใช้จ่าย (Cost Efficiency & Billing)**, **ความมั่นคงปลอดภัยทางการเงิน (Budget Safeguard)** และ **ระบบการรับส่งงานเบื้องหลังแบบคิว (Pub/Sub & Cloud Tasks)** เพื่อเตรียมพร้อมก่อนการขยายระบบ

เพื่อไม่ให้เนื้อหาและขนาดของแต่ละ Merge Request (MR) มีความซับซ้อน หรือมีขนาดการเปลี่ยนแปลงโค้ด (diff size) ที่ใหญ่เกินไปจนรีวิวยาก จึงได้จัดกลุ่มประเด็นการพัฒนา (Batching) ใหม่ โดยผูกหัวข้อที่เชื่อมโยงกันในเชิงสถาปัตยกรรมเข้าด้วยกันดังนี้:

---

## Proposed Batching Strategy

### 📦 Batch 1: Code Optimization & Queue Architecture (การปรับปรุงระดับแอปพลิเคชันและการคิว)
*   **เป้าหมาย:** ปรับปรุงวิธีการดึง/เขียนไฟล์ และเปลี่ยนช่องทางการประมวลผลงานหนักให้ทำงานเป็น Asynchronous Queue เพื่อประหยัด Computing Time ของ Cloud Run หลัก
*   **Issues ในกลุ่ม:**
    *   **[Issue #71]** Optimize Cloud Storage Fetching & Remove Blocking I/O in Radar Processor
        *   *ขอบเขตงาน:* เปลี่ยน Logic การประมวลผลเรดาร์ให้ใช้ Non-blocking I/O และ RAM buffer (เช่น `BytesIO`) แทนการเขียนดิสก์ ซึ่งช่วยลดเวลาการจัดสรร Container (Compute time/Instance-seconds)
    *   **[Issue #65]** Refactor: Migrate long-running background tasks to Google Cloud Tasks / PubSub
        *   *ขอบเขตงาน:* ปรับปรุง Webhook endpoints ให้ส่งข้อมูลเข้า Queue ทันทีแทนการประมวลผลแบบค้างสาย HTTP เพื่อป้องกันการเกิด Request Timeout และคุม Concurrency การดึงข้อมูลเรดาร์
*   **ขนาด MR คาดการณ์:** **Medium - Large** (สถาปัตยกรรมของตัวประมวลผลเรดาร์และโมดูลรับส่ง webhook)
*   **เหตุผลการจัดกลุ่ม:** ทั้งสองเรื่องเป็นการแก้ไขในส่วนของ **Application Logic** การทำควบคู่กันช่วยให้เราสามารถออกแบบโมเดลการประมวลผลแบบ Asynchronous ของ Radar Processor และตัว Worker ของ Queue/PubSub ให้เข้าคู่กันได้ในรอบเดียว

---

### 📦 Batch 2: Infrastructure safeguards & Billing Fine-Tuning (ความปลอดภัยการเงินและการตั้งค่า Cloud)
*   **เป้าหมาย:** วางระบบปิดตัวเองเมื่อเกิดค่าใช้จ่ายผิดปกติ และจูนประสิทธิภาพเครื่องให้สอดคล้องกับค่าใช้จ่ายจริง
*   **Issues ในกลุ่ม:**
    *   **[Issue #72]** Budget-based Auto-shutdown Mechanism for Cloud Run
        *   *ขอบเขตงาน:* ตั้งค่าระบบ GCP Budget Alert ส่งข้อมูลผ่าน Pub/Sub เพื่อสั่งปรับสเกลจำกัดจำนวน max-instances ของ Cloud Run ลงเหลือ 0 เมื่อถึงขอบเขตงบประมาณที่กำหนดไว้
    *   **[Issue #69]** Enhancement: System Infrastructure and Code Optimization (Latency & Billing)
        *   *ขอบเขตงาน:* ปรับแต่งสเปกทรัพยากร (Memory/CPU allocation), ค่า Concurrency limit และช่วงการสเกลของ Container บน Cloud Run ให้มีประสิทธิภาพความคุ้มค่าสูงสุดจากการทำงานแบบ Async ใน Batch 1
*   **ขนาด MR คาดการณ์:** **Medium** (เน้นไฟล์ตั้งค่า IaC/Terraform และการปรับจูนพารามิเตอร์ Cloud Run)
*   **เหตุผลการจัดกลุ่ม:** ทั้งสองเรื่องเกี่ยวข้องกับ **Infrastructure & Cloud Settings** การทำระบบควบคุมงบประมาณ (Issue 72) ร่วมกับการจำกัดทรัพยากร/ขนาดเครื่อง (Issue 69) ช่วยให้มั่นใจว่าการจัดงบประมาณและทรัพยากรฝั่ง Cloud จะอยู่ในสถานะเหมาะสมและปลอดภัยสูงสุดพร้อมๆ กัน

---

## Status Check (อัปเดต ณ 16 มิ.ย. 2026)
*   **Issue #31** (*Wind Vector Nowcasting*) ได้เปลี่ยนสถานะเป็น **Done** แล้ว (ปิดประเด็นบน GitLab เรียบร้อยแล้ว)
*   **Batch 1 (Issue #71 & #65)** ได้ดำเนินการเสร็จสมบูรณ์ในเวอร์ชัน `0.27.0` แล้ว (สถานะ: **Done**)
*   **Batch 2 (Issue #72 & #69)** เตรียมพร้อมสำหรับการดำเนินการเป็นลำดับถัดไป (สถานะ: **Open**)
