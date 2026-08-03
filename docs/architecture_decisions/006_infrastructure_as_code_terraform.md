# ADR 006: Infrastructure as Code (IaC) and Secrets Management

## Status
Accepted

## Context
ปัจจุบันการ Deploy โปรเจกต์ FonMaYang ไปยัง Google Cloud Run ทำผ่านคำสั่ง `gcloud run deploy` ใน GitLab CI/CD โดยส่ง Environment Variables (Env Vars) ทั้งหมดผ่าน flag `--set-env-vars` 
วิธีนี้ทำให้ไฟล์ `.gitlab-ci.yml` รก อ่านยาก และที่สำคัญคือ API Keys รวมถึงข้อมูลที่เป็นความลับอื่นๆ ถูกผูกไว้กับ CI/CD Pipeline โดยตรง ซึ่งมีความเสี่ยงด้านความปลอดภัย (Security risk) นอกจากนี้เมื่อมีการแก้ไข Environment Variables จะทำให้ Cloud Run เกิดการ Deploy ใหม่ทุกครั้งโดยไม่จำเป็น

## Decisions

### 1. Terraform for Infrastructure as Code (IaC)
เราตัดสินใจใช้ **Terraform** เพื่อจัดการ Infrastructure บน Google Cloud (เช่น Cloud Run, Firestore, Secret Manager) แทนการใช้ Shell Script
- **State Management:** จะใช้ Google Cloud Storage (GCS) เป็น Backend สำหรับเก็บไฟล์ `terraform.tfstate` เพื่อให้ทีมงานและระบบ CI/CD เข้าถึง State ตรงกันและป้องกันปัญหา State Lock
- **Separation of Concerns:** GitLab CI/CD จะมีหน้าที่เพียง Build Docker Image และ Push ขึ้น Artifact Registry (หรือ Container Registry) ส่วนขั้นตอนการอัปเดตระบบและตั้งค่า Environment จะเป็นหน้าที่ของ Terraform

### 2. Google Secret Manager for Secrets Management
เราจะย้ายข้อมูลความลับทั้งหมด (เช่น `TELEGRAM_BOT_TOKEN`, `TOMORROW_API_KEY`, `XWEATHER_CLIENT_SECRET`) ไปเก็บไว้ใน **Google Secret Manager**
- Cloud Run จะดึงความลับเหล่านี้โดยตรงจาก Secret Manager ตอน Startup Container
- ข้อมูลความลับจะไม่หลุดไปอยู่ใน `.gitlab-ci.yml` หรือ GitLab CI/CD Variables อีกต่อไป (ยกเว้น GCP Service Account Key ที่จำเป็นต้องใช้ยืนยันตัวตน)
- ช่วยลดปัญหาเรื่อง Quota/Limits ใน GitLab CI Variables และเพิ่มระดับความปลอดภัยสูงสุด

## Consequences
- **Positive:** ความปลอดภัยเพิ่มขึ้นอย่างมาก เพราะโค้ดและ CI/CD จะไม่มีข้อมูล API Key หลุดออกไป
- **Positive:** `.gitlab-ci.yml` จะสะอาดและสั้นลงมาก
- **Positive:** Infrastructure จะถูกทำ Version Control สามารถ Review และทำ Audit ย้อนหลังได้
- **Negative:** มี Learning Curve เล็กน้อยสำหรับทีมพัฒนาที่ต้องเรียนรู้ HCL (HashiCorp Configuration Language) และ Terraform CLI
- **Cost:** ค่าใช้จ่ายของ GCS ในการเก็บ State file ต่ำมาก (ใกล้เคียงฟรี) และ Secret Manager มี Free Tier รองรับเพียงพอต่อโปรเจกต์ขนาดกลาง

## Cloud Platform Note

- สำหรับ FonMaYang ตอนนี้ให้ถือว่า **GCP เป็น platform หลัก** สำหรับ production และ operations เพราะ fit กับ Cloud Run, IAP-style access, และ serverless workflow ที่ทีมใช้อยู่
- **AWS** ควรถือเป็น platform สำรอง/สนามทดลอง/benchmark สำหรับเรียนรู้ enterprise patterns มากกว่าจะเป็น target หลักในระยะสั้น
- ถ้ามี proposal จะย้าย production ไป AWS ให้ประเมิน cost, ops complexity, and service parity เป็นแพ็กเดียวก่อนตัดสินใจ

## Cost Hotspot Note

- GCP มักดูแพงเมื่อ workload ไปหนักที่ **network isolation, Cloud NAT, internal load balancing, logging/monitoring, และ BigQuery scan volume**
- AWS มักดูแพงเมื่อ workload ไปหนักที่ **Client VPN / Verified Access, NAT Gateway, ALB/LCU, และ CloudWatch logs/metrics**
- สำหรับ FonMaYang ถ้าจะควบคุมงบให้ดี ให้เริ่มจาก **serverless + access control ที่เบา** ก่อน แล้วค่อยเพิ่ม network isolation เฉพาะจุดที่จำเป็นจริง

## Cost Hotspot Matrix

| Env | GCP cost hotspot | AWS cost hotspot | Practical note |
|---|---|---|---|
| dev | Logs/metrics จากการ debug ถี่, BigQuery query ซ้ำ, Cloud Run instance ค้างถ้าเปิด always-on โดยไม่จำเป็น | VPN endpoint ชั่วโมงเปิดทิ้ง, CloudWatch logs/metrics เยอะ, NAT สำหรับ developer traffic | ใช้ corporate-style เป็นค่าเริ่มต้น และจำกัด retention/log sampling |
| staging | Internal LB / Cloud NAT ถ้าเริ่มจำลอง private path, monitoring ที่ละเอียดเกินจำเป็น, query/export ซ้ำจาก test data | Client VPN สำหรับทีม QA, ALB/LCU, CloudWatch, NAT Gateway | ให้ staging mirror prod เฉพาะ behavior ที่ต้องทดสอบ ไม่ต้อง mirror ทุก network cost |
| prod | BigQuery scan volume, Cloud Logging ingestion, Cloud NAT + internal LB ถ้ามี private egress, Cloud Run always-on | Verified Access / Client VPN, NAT Gateway, ALB/LCU, CloudWatch logs/metrics | ให้ prod จ่ายเฉพาะสิ่งที่เพิ่ม reliability/security จริง ๆ และเก็บ observability แบบมี budget |
