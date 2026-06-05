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
