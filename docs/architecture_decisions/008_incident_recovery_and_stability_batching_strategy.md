# Architecture Decision Record 008: Incident Recovery & Long-term Stability Batching Strategy

## Context

เมื่อวันที่ 10–17 มิถุนายน 2568 ระบบ FonMaYang เผชิญกับเหตุการณ์ฉุกเฉิน (Incident #84) ที่ส่งผลให้ค่าใช้จ่ายบน Cloud Run พุ่งสูงอย่างผิดปกติถึง 2,657,500% สาเหตุหลักมาจากปัจจัยที่ทับซ้อนกัน 3 ประการ ได้แก่:

1. **OCR Fallback Trap** — Fallback Chain ใน `ocr_service.py` ที่ชนโควต้า Cloud Vision + Gemini ทำให้แต่ละ Request ใช้เวลา 1–2 นาที
2. **WebSocket vs Cloud Run Architecture** — `start_emsc_websocket` รันอยู่บน Cloud Run ที่เปิด CPU Throttling ทำให้เกิด Memory Leak และบล็อก Scale-to-Zero
3. **Cloud Scheduler Retry Flood** — Scheduler เข้าใจว่า Job ล้มเหลว จึงยิง Auto-Retry ทุก 5 นาที

เพื่อให้การแก้ไขเป็นระเบียบ ตรวจสอบได้ และป้องกันไม่ให้ปัญหาเกิดซ้ำ จึงจัดกลุ่มงาน (Batching) แบบแยกชั้น (Layer) ตามลำดับความเร่งด่วน

**FinOps Score ณ วันที่เกิด Incident:** 3.5/5.0 (Medium)
**เป้าหมาย FinOps Score:** ≥ 4.5/5.0

---

## Batching Strategy: Recovery Phases

```
[Phase 0: Stop Bleeding]  →  [Phase 1: Hotfix Code]  →  [Phase 2: Infra Hardening]  →  [Phase 3: Architecture]  →  [Phase 4: Feature Backlog]
      (ทันที)                    (MR + Deploy)               (Infra Fix)                  (วางแผน + Impl)             (หลังระบบเสถียร)
```

---

### 🔴 Phase 0 — Stop Bleeding (ทีม Infra ทำทันทีผ่าน GCP Console)

**เป้าหมาย:** หยุดค่าใช้จ่ายที่กำลังไหลอยู่ให้เร็วที่สุด โดยไม่ต้องรอ Code Merge

| Issue | รายละเอียด | ทำโดย |
|-------|-----------|-------|
| [#87](https://gitlab.com/oatricedev/FonMaYang/-/work_items/87) | Pause `fonmayang-check-rain` Scheduler + จำกัด `max-instances: 2` | Infra |

**คำสั่งสำคัญ:**
```bash
# Pause Scheduler
gcloud scheduler jobs pause fonmayang-check-rain --location=asia-southeast1

# จำกัด Autoscaling
gcloud run services update fontokmai-api --max-instances 2 --region asia-southeast1
```

**ขนาด MR:** ❌ ไม่มี Code Change (ทำผ่าน Console/CLI เท่านั้น)

---

### 🟠 Phase 1 — Hotfix Code (Backend Dev — ทำพร้อมกันได้)

**เป้าหมาย:** แก้ไข Root Cause ระดับโค้ดให้ Request ทำงานเร็วและ Memory ไม่ Leak

| Issue | รายละเอียด | ไฟล์ที่เกี่ยวข้อง | ขนาด MR |
|-------|-----------|-----------------|---------|
| [#85](https://gitlab.com/oatricedev/FonMaYang/-/work_items/85) | Bypass OCR Fallback → เรียก OCR.space โดยตรง พร้อม Fail-fast Timeout | `app/services/ocr_service.py` | Small |
| [#86](https://gitlab.com/oatricedev/FonMaYang/-/work_items/86) | Disable EMSC WebSocket ชั่วคราว | `app/main.py` | Small |

**เหตุผลการจัดกลุ่ม:** ทั้งสองเป็นการแก้ไขระดับ Application Code ที่เล็กและอิสระต่อกัน สามารถทำใน Branch เดียวกันหรือ MR เดี่ยวๆ ก็ได้ตามความถนัด แต่ไม่ควรรวมกับ Infrastructure Change เพื่อให้ Rollback ได้ง่าย

**ผลลัพธ์ที่คาดหวัง:**
- Latency `/api/v1/cron/check-rain`: หลักนาที → ไม่เกิน 5–10 วินาที
- Scale-to-Zero: ทำงานได้ปกติหลัง Container ว่างงาน
- Memory Baseline: ลดลงอย่างมีนัยสำคัญ

**ลำดับ Deploy:** Phase 0 ต้องเสร็จก่อน → Merge Phase 1 → Monitor → Resume Scheduler

---

### 🟡 Phase 2 — Infrastructure Hardening (ทีม Infra — ทำหลัง Phase 1 Deploy)

**เป้าหมาย:** แก้ไขการตั้งค่า Infrastructure ที่เป็นต้นตอให้ Retry Flood ไม่เกิดซ้ำอีก

| Issue | รายละเอียด | ไฟล์ที่เกี่ยวข้อง | ขนาด MR |
|-------|-----------|-----------------|---------|
| [#88](https://gitlab.com/oatricedev/FonMaYang/-/work_items/88) | แก้ Cloud Scheduler Retry Policy (`--max-retry-attempts=0` หรือ 1 ครั้ง) + อัปเดต `setup_schedulers.sh` | `backend/scripts/setup_schedulers.sh` | Small (Script) |

**เหตุผลการจัดกลุ่ม:** แยกออกจาก Phase 0 เพราะนี่คือการแก้ให้ถูกต้องถาวร (Policy Fix) ไม่ใช่การปิดชั่วคราว ควรทำหลังจาก Monitor ระบบแล้ว 1-2 วัน เพื่อยืนยัน Root Cause

---

### 🟢 Phase 3 — Architecture Decision (วางแผน + Implement — ระยะกลาง)

**เป้าหมาย:** แก้ปัญหา WebSocket ด้วยสถาปัตยกรรมที่ถูกต้องในระยะยาว

| Issue | รายละเอียด | ขนาด MR |
|-------|-----------|---------|
| [#89](https://gitlab.com/oatricedev/FonMaYang/-/work_items/89) | Decouple EMSC WebSocket ออกจาก API หลัก: เลือกแนวทางจาก 4 ตัวเลือก (VM / Polling / CPU Always-On / Worker Service) | Medium–Large |

⚠️ **Large MR Mitigation:** หากตัดสินใจเลือก Option A (แยก Cloud Run Worker) จะมีผลกระทบวงกว้างต่อ Dockerfile และ CI/CD Pipeline จะต้องพิจารณาแตก Issue ย่อยสำหรับการตั้งค่า Infrastructure ออกจาก Application Logic

**ตัวเลือกที่ต้องประเมิน (ก่อน Implement):**

| ตัวเลือก | วิธี | Cost | Complexity |
|---------|-----|------|-----------|
| A | Cloud Run Worker แยก (CPU Always Allocated + maxScale:1) | ~฿15–30/เดือน | Medium |
| B | เปลี่ยนเป็น Polling ผ่าน REST API | ต่ำมาก | Low |
| C | ตั้งค่า CPU Always-On บน API Service เดิม | ~฿15–30/เดือน | Low |
| D | Compute Engine e2-micro (Free Tier) | ฟรี | High (ดูแล VM) |

**ขั้นตอน:**
1. ตัดสินใจเลือก Option (ประชุมทีม)
2. เขียน ADR ย่อยบันทึกเหตุผล
3. Implement + เพิ่ม Monitoring
4. ปิด Hotfix ใน Issue #86

---

### 🔵 Phase 4 — Feature Backlog (หลังระบบเสถียร)

**เป้าหมาย:** งาน Feature ที่ค้างอยู่ก่อน Incident ที่ยังไม่ได้ถูก Batch และยังเปิดอยู่

#### 📦 Batch M: Observability & FinOps (ต่อเนื่องจาก Batch 2 เดิม)

*ฟีเจอร์ที่ช่วยให้มองเห็นและควบคุมค่าใช้จ่าย — ควรทำเร็วหลัง Incident เพื่อป้องกันซ้ำ*

| Issue | รายละเอียด |
|-------|-----------|
| [#73](https://gitlab.com/oatricedev/FonMaYang/-/issues/73) | Verify Performance Gains & Monitor Memory Usage Post-Deployment of #71 |
| [#74](https://gitlab.com/oatricedev/FonMaYang/-/issues/74) | Add Cloud Tasks Queue Monitoring & API endpoint |
| [#79](https://gitlab.com/oatricedev/FonMaYang/-/issues/79) | Infrastructure: Setup System Uptime Monitoring & Status Dashboard |
| [#83](https://gitlab.com/oatricedev/FonMaYang/-/issues/83) | Optimization: Cleanup old Docker Images in Artifact Registry |

**เหตุผลการจัดกลุ่ม:** ทั้งหมดเป็น Observability และ Housekeeping ที่ไม่มี Dependency ซับซ้อนต่อกัน สามารถทำคู่ขนานได้

**ขนาด MR คาดการณ์:** Small–Medium ต่อ Issue

---

#### 📦 Batch N: Budget & Cost Automation (FinOps Intelligence)

*ระบบป้องกันค่าใช้จ่ายอัตโนมัติ — ป้องกัน Incident แบบนี้ไม่ให้เกิดซ้ำโดยไม่ต้องมีคนดู*

| Issue | รายละเอียด |
|-------|-----------|
| [#80](https://gitlab.com/oatricedev/FonMaYang/-/issues/80) | Feature: Route billing and system alerts to dedicated DevBot |
| [#81](https://gitlab.com/oatricedev/FonMaYang/-/issues/81) | Feature: Adjust GCP Budget via Telegram command (/setbudget) |

**เหตุผลการจัดกลุ่ม:** ทั้งสองเรื่องเกี่ยวข้องกับ Bot Routing และ Budget Command โดยตรง

**Dependency:** ต้องการ #80 (Bot Routing) ก่อนจึงทำ #81 ได้

**ขนาด MR คาดการณ์:** Medium

---

#### 📦 Batch O: Security & Secret Management

*ยกระดับความปลอดภัยของ Secrets และ Environment Variables*

| Issue | รายละเอียด |
|-------|-----------|
| [#75](https://gitlab.com/oatricedev/FonMaYang/-/issues/75) | [Epic] Environment Staging & Automated Secret Management (Local/UAT/PROD) |

**เหตุผลการจัดกลุ่ม:** เป็นงาน Epic ที่ต้องแตะทุกส่วนของระบบ (Secret Manager) ควรทำเป็น Standalone Batch เพื่อป้องกันผลกระทบวงกว้าง

**ขนาด MR คาดการณ์:** Large (Epic) - ควรแตก Issue ย่อยก่อนเริ่ม

---

#### 📦 Batch P: Advanced Infrastructure (IaC & Networking)

*ย้าย Infrastructure สู่ Code และจำกัดการเข้าถึง API*

| Issue | รายละเอียด |
|-------|-----------|
| [#82](https://gitlab.com/oatricedev/FonMaYang/-/issues/82) | Feature: Manage GCP Budget and Alerts via Terraform (IaC) |
| [#78](https://gitlab.com/oatricedev/FonMaYang/-/issues/78) | Architecture: Implement Dedicated Users (Private Cloud Run) with Reverse Proxy / API Gateway |

**เหตุผลการจัดกลุ่ม:** ทั้งสองเป็นงานระดับ Infrastructure ที่ซับซ้อน (Terraform, Reverse Proxy) แยกออกจากโค้ดของแอปพลิเคชันหลักอย่างสิ้นเชิง

**ขนาด MR คาดการณ์:** Large



## Execution Sequence (ภาพรวมลำดับการดำเนินงาน)

```
ปัจจุบัน (17 มิ.ย. 2568)
│
├─[Phase 0]─► Infra: Pause Scheduler + max-instances=2        ← ทำทันทีวันนี้
│
├─[Phase 1]─► Dev: MR แก้ ocr_service.py + main.py            ← ทำภายใน 1–2 วัน
│              └─ Monitor Memory + Latency ≥ 1 วัน
│
├─[Phase 2]─► Infra: แก้ Retry Policy + setup_schedulers.sh   ← หลัง Monitor ผ่าน
│
├─[Phase 3]─► ทีม: ตัดสินใจ WebSocket Architecture            ← ภายใน 1–2 สัปดาห์
│              └─ Implement + ปิด Hotfix #86
│
└─[Phase 4]─► Feature Backlog ตาม Batch M → N → O → P         ← ตามลำดับ Priority
```

---

## Status Table (อัปเดต ณ 17 มิ.ย. 2568)

| Phase / Batch | สถานะ | Issues |
|--------------|-------|--------|
| Phase 0 — Stop Bleeding | 🔴 **รอดำเนินการ (Urgent)** | [#87](https://gitlab.com/oatricedev/FonMaYang/-/work_items/87) |
| Phase 1 — Hotfix Code | 🔴 **รอดำเนินการ (Urgent)** | [#85](https://gitlab.com/oatricedev/FonMaYang/-/work_items/85), [#86](https://gitlab.com/oatricedev/FonMaYang/-/work_items/86) |
| Phase 2 — Infra Hardening | 🟡 **Ready (รอ Phase 1)** | [#88](https://gitlab.com/oatricedev/FonMaYang/-/work_items/88) |
| Phase 3 — Architecture | 🟡 **Ready (รอ Phase 1)** | [#89](https://gitlab.com/oatricedev/FonMaYang/-/work_items/89) |
| Batch M — Observability | 🟢 **Backlog** | [#73](https://gitlab.com/oatricedev/FonMaYang/-/issues/73), [#74](https://gitlab.com/oatricedev/FonMaYang/-/issues/74), [#79](https://gitlab.com/oatricedev/FonMaYang/-/issues/79), [#83](https://gitlab.com/oatricedev/FonMaYang/-/issues/83) |
| Batch N — Budget Automation | 🟢 **Backlog** | [#80](https://gitlab.com/oatricedev/FonMaYang/-/issues/80), [#81](https://gitlab.com/oatricedev/FonMaYang/-/issues/81) |
| Batch O — Security & Secrets | 🟢 **Backlog (Low Priority)** | [#75](https://gitlab.com/oatricedev/FonMaYang/-/issues/75) |
| Batch P — Advanced Infra (IaC) | 🟢 **Backlog (Low Priority)** | [#82](https://gitlab.com/oatricedev/FonMaYang/-/issues/82), [#78](https://gitlab.com/oatricedev/FonMaYang/-/issues/78) |
