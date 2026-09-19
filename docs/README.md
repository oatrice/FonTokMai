# FonMaYang Documentation

เอกสารหลักในโฟลเดอร์นี้เกี่ยวข้องกับการพัฒนาและการติดตั้งเฉพาะของ **Backend & Bot Service** (Cloud Run, FastAPI, Worker)

---

## 🌐 Central Architecture & Single Source of Truth (SSOT)
เอกสารสถาปัตยกรรมระดับภาพรวมของทั้งระบบ (Cross-Platform), Architecture Decision Records (ADR), และ Product Specifications ได้ย้ายไปยัง repository กลางแล้ว:

👉 **[FonTokMai-Docs (GitLab)](https://gitlab.com/oatricedev/FonTokMai-Docs)**

### รายการเอกสารที่ย้ายไปที่ Repo กลาง:
- **Architecture Decision Records (ADRs):**
  - ADR-0001: บันทึกการใช้ Central Documentation Repository
  - ADR-0002: On-Device Radar Architecture & Processing
  - Historical Backend Archive: ADR 001 - 011
- **System Architecture & Radar:**
  - System Context & Overview Diagram
  - Epic On-Device Radar Plan
  - Radar Status Monitoring Architecture
  - Web App Architecture & Sitemap
- **Product & Specifications:**
  - Product Roadmap
  - System Specifications & Requirements

---

## 🛠 เอกสารเฉพาะ Backend ที่ยังคงอยู่ใน Repo นี้
- `development_guide.md`: คู่มือการพัฒนาและทดสอบ Local Backend
- `deployment_and_change_management.md`: ขั้นตอนการ Deploy Cloud Run
- `gitlab_runner_setup.md`: การตั้งค่า GitLab CI Runner
- `manual_integration_testing.md`: สคริปต์และการทดสอบ Manual Integration
- `cloud_tasks_dashboard_analysis.md`: การวิเคราะห์ Cloud Tasks
- `fonmayang_cloudrun_metrics_report.md`: รายงานประสิทธิภาพ Cloud Run

- [UX/UI Flow Architectural Evaluation (5 Paradigms)](./ux_flow_architectural_eval.md)
