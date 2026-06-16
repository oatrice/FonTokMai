# Implementation Plan: Batch 2 — Infrastructure Safeguards & Billing Fine-Tuning

## Background

Batch 1 (v0.27.0) เสร็จสมบูรณ์แล้ว ขั้นตอนนี้คือ **Batch 2** ตาม ADR 007 ซึ่งมีเป้าหมายในการสร้างระบบ Safety Net ด้านการเงินและปรับจูนประสิทธิภาพ Cloud Run ให้เหมาะสมกับ Workload จริงหลังจากทำ Async Queue ใน Batch 1

---

## เนื้อหาที่ต้องทำ

### Issue #72 — Budget-based Auto-shutdown via Pub/Sub
> วางระบบให้ GCP ส่ง Budget Alert → Pub/Sub → Cloud Function → ปิด Cloud Run (max-instances=0)

### Issue #69 — Cloud Run Parameter Tuning
> ปรับค่า Memory, CPU, Concurrency ของ Cloud Run ให้คุ้มค่าสูงสุด

---

## Open Questions

> [!IMPORTANT]
> โปรดยืนยันข้อมูลต่อไปนี้ก่อนดำเนินการ:
>
> 1. **งบประมาณ (Budget Threshold):** ต้องการตั้ง Budget Alert ที่จำนวนเงินเท่าไหร่? (เช่น $10/เดือน, $20/เดือน)
> 2. **Currency:** ใช้สกุลเงิน USD หรือ THB?
> 3. **Alert Action:** เมื่อถึง threshold ต้องการ:
>    - (a) ปิดทันทีที่ 100% ของ budget หรือ
>    - (b) ส่ง warning ที่ 80% และ ปิดที่ 100%?
> 4. **Cloud Function vs. Cloud Run Job:** สำหรับ Budget Alert Handler ต้องการใช้ Cloud Function (Gen2) หรือจะเขียนเป็น endpoint ใน Cloud Run เอง?

> [!WARNING]
> **Terraform vs. Shell Script:** โปรเจกต์ปัจจุบันใช้ Shell Scripts (`setup_gcp.sh`, `setup_schedulers.sh`) ไม่มี Terraform ควรดำเนินการอย่างไร:
> - (a) ยังคงใช้ Shell Script (`gcloud` CLI) — สอดคล้องกับ pattern ปัจจุบัน
> - (b) เพิ่ม Terraform เป็น IaC ครั้งแรก — ซับซ้อนกว่าแต่ maintainable ในระยะยาว

---

## สถาปัตยกรรม Issue #72 (Budget Auto-shutdown)

```
GCP Billing Budget
       │
       │ Budget Alert (at 100%)
       ▼
   Pub/Sub Topic: "billing-alerts"
       │
       │ Push Subscription
       ▼
   Cloud Function (Gen2) หรือ Cloud Run endpoint
   "budget-shutdown-handler"
       │
       │ gcloud run services update --max-instances=0
       ▼
   Cloud Run: fontokmai-api → SCALED TO ZERO
```

---

## Proposed Changes

### ────────────────────────────────────────
### Component 1: GCP Budget & Pub/Sub Setup (Issue #72)

#### [NEW] backend/scripts/setup_budget_alert.sh
สคริปต์สำหรับสร้าง Pub/Sub topic, subscription, GCP Budget Alert โดยใช้ `gcloud billing budgets create`

**เนื้อหา:**
- สร้าง Pub/Sub topic `billing-alerts`
- สร้าง Budget Alert ผ่าน `gcloud billing budgets create` เชื่อมกับ topic
- ตั้ง threshold rules: 80% (notification only) + 100% (trigger Pub/Sub)

#### [NEW] backend/app/routers/budget_webhook.py
FastAPI router ที่รับ Pub/Sub push notification จาก Budget Alert

**เนื้อหา:**
- Endpoint: `POST /api/v1/internal/budget-alert`
- ตรวจสอบ Pub/Sub message signature
- ถ้า `costAmount / budgetAmount >= 1.0` → เรียก `gcloud run services update --max-instances=0`
- ส่งแจ้งเตือนผ่าน Telegram

#### [MODIFY] backend/app/main.py
- Register `budget_webhook` router ใหม่

#### [MODIFY] backend/scripts/setup_gcp.sh
- เพิ่มการตั้งค่า IAM permission สำหรับ Pub/Sub service account เพื่อ invoke Cloud Run

### ────────────────────────────────────────
### Component 2: Cloud Run Parameter Tuning (Issue #69)

#### [MODIFY] .gitlab-ci.yml

ปรับพารามิเตอร์ `gcloud run deploy` ดังนี้:

| Parameter | ค่าปัจจุบัน | ค่าใหม่ที่แนะนำ | เหตุผล |
|---|---|---|---|
| `--memory` | `1024Mi` | `512Mi` | หลัง Batch 1 ไม่มี blocking I/O แล้ว RAM ลดได้ |
| `--concurrency` | `80` | `40` | ลด concurrency ให้สอดคล้องกับ async worker pattern |
| `--cpu` | (ไม่ได้กำหนด, default 1) | `1` | เพิ่มให้ชัดเจน |
| `--timeout` | (default 300s) | `120s` | webhook timeout สั้นลงตาม Async pattern |
| `--service-max-instances` | `2` | `3` | buffer นิดหน่อยสำหรับ peak load |

> [!NOTE]
> ค่าเหล่านี้ยังเป็น "แนะนำ" — ควรทำ Load Test เพื่อยืนยันก่อน merge

#### [MODIFY] backend/scripts/setup_budget_alert.sh *(ใหม่จาก Component 1)*
- เพิ่ม variable สำหรับ BUDGET_AMOUNT และ BILLING_ACCOUNT_ID

#### [MODIFY] backend/.env.example
- เพิ่ม `BUDGET_PUBSUB_TOPIC=billing-alerts`
- เพิ่ว `GCP_BILLING_ACCOUNT_ID=`

### ────────────────────────────────────────
### Component 3: CI/CD Integration

#### [MODIFY] .gitlab-ci.yml
- เพิ่ม step `setup_budget` ใน deploy stage เพื่อรัน `setup_budget_alert.sh` อัตโนมัติ
- เพิ่ม GitLab CI Variable: `GCP_BILLING_ACCOUNT_ID`, `BUDGET_AMOUNT_USD`

---

## ไฟล์สรุปที่ต้องสร้างหรือแก้ไข

| ไฟล์ | สถานะ | Issue |
|---|---|---|
| `backend/scripts/setup_budget_alert.sh` | **NEW** | #72 |
| `backend/app/routers/budget_webhook.py` | **NEW** | #72 |
| `backend/app/main.py` | MODIFY | #72 |
| `backend/scripts/setup_gcp.sh` | MODIFY | #72 |
| `backend/.env.example` | MODIFY | #72 & #69 |
| `.gitlab-ci.yml` | MODIFY | #69 & #72 |
| `docs/features/[issue-72]/...` | NEW (docs) | #72 |
| `docs/features/[issue-69]/...` | NEW (docs) | #69 |

---

## Verification Plan

### Automated Tests
- เพิ่ม unit test สำหรับ `budget_webhook.py` endpoint
- ทดสอบ Pub/Sub message parsing logic

### Manual Verification
1. รัน `setup_budget_alert.sh` แล้ว verify ใน GCP Console ว่า Budget และ Pub/Sub topic ถูกสร้างขึ้น
2. ทดสอบ endpoint `/api/v1/internal/budget-alert` ด้วย mock Pub/Sub payload
3. ตรวจสอบว่า Cloud Run scale down เป็น `--max-instances=0` ได้จริง
4. ตรวจสอบ Telegram notification ว่าส่งแจ้งเตือน budget alert ได้

---

## ลำดับการดำเนินงาน

```
Step 1: ตอบคำถามใน Open Questions (ต้องการ input จากคุณ)
   │
   ▼
Step 2: สร้าง setup_budget_alert.sh + ขอ GCP billing account info
   │
   ▼
Step 3: สร้าง budget_webhook.py router + unit tests
   │
   ▼
Step 4: ปรับ Cloud Run parameters ใน .gitlab-ci.yml (Issue #69)
   │
   ▼
Step 5: เพิ่ม CI/CD integration + docs
   │
   ▼
Step 6: Manual verification checklist
```
