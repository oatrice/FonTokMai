# Implementation Plan: Batch 2 — Infrastructure Safeguards & Billing Fine-Tuning

## Background

Batch 1 (v0.27.0) เสร็จสมบูรณ์แล้ว ขั้นตอนนี้คือ **Batch 2** ตาม ADR 007 ซึ่งมีเป้าหมายในการสร้างระบบ Safety Net ด้านการเงินและปรับจูนประสิทธิภาพ Cloud Run ให้เหมาะสมกับ Workload จริงหลังจากทำ Async Queue ใน Batch 1

จากการตรวจสอบ Issue Description ในภายหลัง พบว่า Issue #69 มีขอบเขตงานกว้างกว่าที่วางแผนไว้ครั้งแรก จึงได้เพิ่ม **Code Optimization Sub-tasks** เพิ่มเติม

---

## เนื้อหาที่ต้องทำ

### Issue #72 — Budget-based Auto-shutdown via Pub/Sub
> วางระบบให้ GCP ส่ง Budget Alert → Pub/Sub → Cloud Run endpoint → ปิด Cloud Run (max-instances=0)

### Issue #69 — Cloud Run Parameter Tuning + Code Optimization
> ปรับค่า Memory, CPU, Concurrency ของ Cloud Run + แก้ Dead URL, Async Parallel, Cloud Logging

---

## สถาปัตยกรรม Issue #72 (Budget Auto-shutdown)

```
GCP Billing Budget
       │
       │ Budget Alert (at 80% → warning, at 100% → shutdown)
       ▼
   Pub/Sub Topic: "billing-alerts"
       │
       │ Push Subscription
       ▼
   POST /api/v1/internal/budget-alert  (Cloud Run endpoint)
       │
       ├── 80%  → ส่ง Telegram warning เท่านั้น
       └── 100% → gcloud run services update --max-instances=0
                   + ส่ง Telegram emergency alert
```

> **Design Decision:** ใช้ Cloud Run endpoint แทน Cloud Function แยกต่างหาก
> เพื่อลด infrastructure complexity และ cost (ไม่ต้องสร้าง GCF ใหม่)

---

## Proposed Changes

### ────────────────────────────────────────
### Component 1: GCP Budget & Pub/Sub Setup (Issue #72) ✅

#### [NEW] backend/scripts/setup_budget_alert.sh
- สร้าง Pub/Sub topic `billing-alerts`
- สร้าง Push subscription ชี้ไปที่ Cloud Run URL
- สร้าง Budget Alert ผ่าน `gcloud billing budgets create` (80% warning + 100% trigger)
- Grant `roles/run.invoker` ให้ Pub/Sub service account

#### [NEW] backend/app/routers/budget_webhook.py
- `POST /api/v1/internal/budget-alert`
- Parse Pub/Sub push message (base64 JSON)
- 80% → Telegram warning, 100% → `gcloud run services update --max-instances=0`

#### [MODIFY] backend/app/main.py
- Register `budget_webhook` router ✅

#### [MODIFY] backend/scripts/setup_gcp.sh
- เพิ่ม Cloud Logging exclusion filters (Issue #69 เพิ่มเติม)

#### [MODIFY] backend/.env.example
- เพิ่ม `BUDGET_PUBSUB_TOPIC`, `GCP_BILLING_ACCOUNT_ID`, `CLOUD_RUN_SERVICE_NAME`

### ────────────────────────────────────────
### Component 2: Cloud Run Parameter Tuning (Issue #69) ✅

#### [MODIFY] .gitlab-ci.yml

| Parameter | ก่อน | หลัง | เหตุผล |
|---|---|---|---|
| `--memory` | `1024Mi` | `512Mi` | หลัง Batch 1 ไม่มี blocking I/O แล้ว RAM ลดได้ |
| `--concurrency` | `80` | `40` | ลด concurrency ให้สอดคล้องกับ async worker pattern |
| `--cpu` | (default 1) | `1` | เพิ่มให้ชัดเจน |
| `--timeout` | (default 300s) | `120s` | webhook timeout สั้นลงตาม Async pattern |
| `--service-max-instances` | `2` | `3` | buffer สำหรับ peak load |

### ────────────────────────────────────────
### Component 3: Issue #69 Code Optimization Sub-tasks ✅

#### Sub-task 1: Fix Dead URL (kkn120Loop.gif → 404)

**Root Cause ที่พบ:**
ใน `tmd_radar_processor.py` มี fallback URL construction ที่สร้าง URL ผิด:
```python
# ❌ เดิม (ผิด — สร้าง kkn120Loop.gif ซึ่ง 404)
url = getattr(self.config, 'loop_gif_url',
    self.config.static_image_url.replace('_latest.gif', 'Loop.gif'))
```

**ผลการ verify URL จาก TMD Server:**

| Station | Loop GIF URL | HTTP Status |
|---|---|---|
| kkn120 | `weather.tmd.go.th/kkn/kkn120Loop.gif` | **404** — ไม่มีจาก TMD |
| kkn240 | `weather.tmd.go.th/kkn/kkn240Loop.gif` | **200 OK** |
| skn240 | `weather.tmd.go.th/skn/skn240Loop.gif` | **200 OK** |

**แก้ไข:**
- เพิ่ม `loop_gif_url: str = ""` field ใน `StationConfig`
- kkn120: `loop_gif_url=""` → skip fetch, ใช้ static image แทน
- kkn240/skn240: hardcode URL จริงที่ verified แล้ว
- Fix fallback logic ใน `tmd_radar_processor.py` + `scheduler_tasks.py`

#### [MODIFY] backend/app/services/tmd_radar_config.py ✅
#### [MODIFY] backend/app/services/tmd_radar_processor.py ✅
#### [MODIFY] backend/app/scheduler_tasks.py ✅

---

#### Sub-task 2: Async Parallel Processing

**Root Cause:** `fetch_tmd_radar_routine()` ทำงาน sequential 3 stations

**แก้ไข:** Refactor เป็น `asyncio.gather()` — 3 stations ทำงาน parallel พร้อมกัน

```python
# หลัง (parallel):
station_results = await asyncio.gather(
    *[_process_station(s) for s in stations_to_update],
    return_exceptions=True
)
```

**ผลที่คาดหวัง:** เวลา fetch 3 stations จาก `3 × T` → `max(T)` ≈ ลดได้ ~60-70%

#### [MODIFY] backend/app/scheduler_tasks.py ✅

> [!NOTE]
> `check_rain_and_alert` loop per-location ยังไม่ทำ parallel เพราะมีความเสี่ยงเรื่อง
> Telegram rate limit (30 msg/s) และ Firestore concurrent write บน `last_alerted_at`

---

#### Sub-task 3: Cloud Logging Noise Reduction

**Root Cause:** EMSC WebSocket log ทุก message ที่ `WARNING` level → Cloud Logging billing leak

**แก้ไข Python-level:**
- Earthquake events จริง: `INFO` (ยังคงไว้)
- Non-earthquake messages (heartbeat, ack): `DEBUG` เท่านั้น
- JSON decode errors: ลด `WARNING` → `DEBUG`
- เพิ่ม rate limiter: log ทุก 100 messages เพื่อ confirm connectivity

**แก้ไข GCP-level:**
- สร้าง Cloud Logging Exclusion Filters ใน `setup_gcp.sh`:
  - `emsc-websocket-debug-noise`: filter EMSC DEBUG messages
  - `httpx-debug-verbose`: filter httpx DEBUG logs

#### [MODIFY] backend/app/services/earthquake.py ✅
#### [MODIFY] backend/scripts/setup_gcp.sh ✅

---

## ไฟล์สรุปที่สร้างหรือแก้ไขทั้งหมด

| ไฟล์ | สถานะ | Issue |
|---|---|---|
| `backend/scripts/setup_budget_alert.sh` | ✅ NEW | #72 |
| `backend/app/routers/budget_webhook.py` | ✅ NEW | #72 |
| `backend/app/main.py` | ✅ MODIFIED | #72 |
| `backend/.env.example` | ✅ MODIFIED | #72 & #69 |
| `.gitlab-ci.yml` | ✅ MODIFIED | #69 & #72 |
| `backend/app/services/tmd_radar_config.py` | ✅ MODIFIED | #69 |
| `backend/app/services/tmd_radar_processor.py` | ✅ MODIFIED | #69 |
| `backend/app/scheduler_tasks.py` | ✅ MODIFIED | #69 |
| `backend/app/services/earthquake.py` | ✅ MODIFIED | #69 |
| `backend/scripts/setup_gcp.sh` | ✅ MODIFIED | #69 & #72 |
| `docs/features/29.../manual_verification.md` | ✅ NEW | #69 & #72 |

---

## Verification Plan

### Manual Verification (Issue #72)
1. ตั้งค่า `GCP_BILLING_ACCOUNT_ID` + `BUDGET_AMOUNT_USD` ใน CI/CD Variables
2. รัน `setup_budget_alert.sh` → verify Budget + Pub/Sub ใน GCP Console
3. ทดสอบ mock 80% → ได้รับ Telegram warning
4. ทดสอบ mock 100% → Cloud Run scale ลงเหลือ 0 + Telegram emergency alert
5. Restore: `gcloud run services update fontokmai-api --max-instances=3`

### Manual Verification (Issue #69 Sub-tasks)
1. ตรวจสอบ `kkn120` ไม่มี 404 error ใน logs
2. วัดเวลา `fetch_tmd_radar_routine` ก่อน/หลัง parallel
3. ตรวจสอบ `gcloud logging exclusions list` แสดง 2 exclusions

ดูรายละเอียดใน [manual_verification.md](./manual_verification.md)
