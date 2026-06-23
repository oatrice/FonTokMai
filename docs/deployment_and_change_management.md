# Deployment and Change Management Guide

เอกสารนี้อธิบายถึงกระบวนการจัดการการเปลี่ยนแปลง (Change Management) และการ Deploy ระบบขึ้น Google Cloud Run เพื่อป้องกันข้อผิดพลาดและควบคุมค่าใช้จ่าย

## หลักการสำคัญ (Core Principles)

1. **ห้ามรันคำสั่ง Deploy จากเครื่อง Local โดยตรง:** การ Deploy และการตั้งค่า Cloud Run ทั้งหมดจะต้องผ่านระบบ GitLab CI/CD เสมอ
2. **Infrastructure as Code (บางส่วน):** การตั้งค่าทรัพยากร (เช่น CPU, Memory, Min Instances) จะถูกเก็บไว้ในโค้ด (ไฟล์ `backend/deploy/cloudrun.env`) เสมอ
3. **ตรวจสอบและอนุมัติ (Review & Approve):** การแก้ไขทรัพยากรที่มีผลกับค่าใช้จ่าย จะต้องถูกตรวจสอบและกดอนุมัติด้วยมือ (Manual Approval) ผ่าน GitLab Pipeline ก่อนนำขึ้น Production

## การแก้ไข Cloud Run Configuration (เช่น ปรับ CPU/Memory หรือ จำนวน Instance)

ไฟล์ **`backend/deploy/cloudrun.env`** คือ Source of Truth ของการตั้งค่า Cloud Run 

### ขั้นตอนการขอแก้ไขตั้งค่า

1. **แก้ไขไฟล์ในเครื่อง Local:**
   แก้ไขค่าในไฟล์ `backend/deploy/cloudrun.env` ตามต้องการ เช่น:
   ```env
   # 2026-06-25: ปรับ min-instances เป็น 1 เพื่อรองรับ Traffic แคมเปญการตลาด
   # หมดแคมเปญให้ปรับกลับเป็น 0
   CLOUD_RUN_MIN_INSTANCES=1
   ```
   > 💡 **Best Practice:** ควรเขียนคอมเมนต์ระบุ **วันที่** และ **เหตุผล (Why)** ควบคู่ไปกับการเปลี่ยนตัวเลขเสมอ เพื่อให้ทีมงานเข้าใจเจตนา

2. **Commit โค้ดและเขียนข้อความอธิบาย:**
   ในการ commit โค้ด ควรเขียนอธิบายเหตุผลสั้นๆ ใน Commit message
   ```bash
   git commit -m "chore: เปลี่ยน min-instances เป็น 1 ชั่วคราวเพื่อรับแคมเปญการตลาด"
   git push origin main
   ```
   *(หรือทำผ่านกระบวนการ Merge Request)*

3. **กดอนุมัติ (Approve) บน GitLab CI/CD:**
   - ไปที่เว็บไซต์ GitLab ของโปรเจ็ค
   - เข้าเมนู **Build > Pipelines**
   - มองหา Pipeline ล่าสุดของ Commit ของคุณ คุณจะเห็นสถานะเป็น **Pause**
   - กดปุ่ม **Play (▶️)** ที่ Job ชื่อ `cloudrun_config_only` 
   - ระบบจะรันสคริปต์บน GitLab Runner เพื่อนำ Config ใหม่ไปอัปเดตให้

## มาตรการป้องกันความผิดพลาด (Guardrails)

สคริปต์ `apply_cloudrun_config.sh` และ `deploy_cloudrun.sh` ถูกป้องกันไม่ให้สามารถรันจากเครื่อง Local ได้โดยไม่ตั้งใจ 
หากคุณพยายามสั่งรันไฟล์ในคอมพิวเตอร์ของคุณเอง สคริปต์จะหยุดทำงานทันทีพร้อมแจ้ง Error 

**กรณีฉุกเฉิน (Emergency Break-Glass):**
หากระบบ CI/CD ล่ม และมีความจำเป็นขั้นสูงสุดที่ต้องแก้ไขด่วนจากเครื่อง Local ให้ส่ง Flag พิเศษต่อท้ายคำสั่ง (มีความเสี่ยง ผู้ดำเนินการต้องรับผิดชอบผลลัพธ์):
```bash
./backend/deploy/apply_cloudrun_config.sh --danger-local-run
```
