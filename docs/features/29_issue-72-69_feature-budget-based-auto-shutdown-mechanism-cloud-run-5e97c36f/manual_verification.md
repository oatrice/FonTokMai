# Manual Verification Guide: Batch 2 (Issue #69 & #72)

## Issue #69 — Cloud Run Parameter Tuning

### การเปลี่ยนแปลง
| Parameter | ก่อน | หลัง |
|---|---|---|
| `--memory` | `1024Mi` | `512Mi` |
| `--cpu` | (default 1) | `1` (ชัดเจน) |
| `--timeout` | (default 300s) | `120s` |
| `--concurrency` | `80` | `40` |
| `--service-max-instances` | `2` | `3` |

### ขั้นตอนตรวจสอบ

1. **ตรวจสอบหลัง deploy:**
   ```bash
   gcloud run services describe fontokmai-api \
     --region asia-southeast1 \
     --format json | jq '{memory: .spec.template.spec.containers[0].resources.limits.memory, concurrency: .spec.containerConcurrency}'
   ```
   ผลลัพธ์ที่ต้องการ: `memory: "512Mi"`, `concurrency: 40`

2. **Load Test (แนะนำ):**
   ```bash
   # ใช้ hey หรือ k6 ทดสอบ
   hey -n 100 -c 20 https://<CLOUD_RUN_URL>/health
   ```

3. **ตรวจสอบ Cost ใน GCP Console:**
   - ไปที่ Cloud Run → Metrics → Container Instance Count
   - ตรวจว่า instance ไม่เกิน 3

---

## Issue #69 — Code Optimization (Sub-tasks เพิ่มเติม)

> งานนี้เพิ่มเติมจาก Cloud Run parameter tuning เดิม ครอบคลุม 3 ส่วน:
> 1. **Fix Dead URL** — `kkn120Loop.gif` ที่ return 404
> 2. **Async Parallel Processing** — `fetch_tmd_radar_routine` ทำ 3 stations พร้อมกัน
> 3. **Cloud Logging Optimization** — ลด EMSC WebSocket noise

---

### Sub-task 1: Fix Dead URL (`kkn120Loop.gif`)

**ผลการ verify URL จริงจาก TMD:**

| URL | HTTP Status | หมายเหตุ |
|---|---|---|
| `weather.tmd.go.th/kkn/kkn120Loop.gif` | **404** | ❌ TMD ไม่มี 120km loop GIF |
| `weather.tmd.go.th/kkn/kkn240Loop.gif` | **200 OK** | ✅ ใช้งานได้ |
| `weather.tmd.go.th/skn/skn240Loop.gif` | **200 OK** | ✅ ใช้งานได้ |

**ตรวจสอบหลัง deploy:**
```bash
# ตรวจว่า kkn120 ไม่มีการ fetch loop GIF อีกต่อไป
# ดู log ว่าต้องเห็น:
# "[kkn120] No loop_gif_url available ... Skipping loop fetch"
gcloud logging read 'textPayload:"No loop_gif_url"' \
  --project=fonmayang \
  --limit=5
```

**ตรวจสอบ Code:**
```bash
python -c "
from app.services.tmd_radar_config import STATIONS
for code, cfg in STATIONS.items():
    print(f'{code}: loop_gif_url={cfg.loop_gif_url!r}')
"
# Expected:
# kkn120: loop_gif_url=''         ← ไม่ fetch, ใช้ static แทน
# kkn240: loop_gif_url='https://weather.tmd.go.th/kkn/kkn240Loop.gif'
# skn240: loop_gif_url='https://weather.tmd.go.th/skn/skn240Loop.gif'
```

---

### Sub-task 2: Async Parallel — `fetch_tmd_radar_routine`

**ตรวจสอบ performance ก่อน/หลัง:**
```bash
# วัดเวลา cron run
time curl -s -X POST https://<CLOUD_RUN_URL>/api/v1/cron/fetch-tmd-radar \
  -H "X-Cron-Secret: $CRON_SECRET"

# เช็ค log ว่าเห็น summary line
gcloud logging read 'textPayload:"TMD Radar Cache Phase complete"' \
  --project=fonmayang \
  --limit=3
# Expected: "TMD Radar Cache Phase complete: 3/3 stations, X.Xs"
```

**ตรวจสอบว่า stations ทำงาน parallel:**
```bash
# ใน log ต้องเห็น 3 stations interleaved กัน (ไม่ sequential)
gcloud logging read 'textPayload:"Cached static image"' \
  --project=fonmayang \
  --limit=10
```

**เป้าหมาย:** เวลา fetch 3 stations ≤ `max(T_single_station)` แทนที่จะเป็น `3 × T`

---

### Sub-task 3: Cloud Logging Optimization

**ตรวจสอบ GCP Logging Exclusion Filters:**
```bash
gcloud logging exclusions list --project=fonmayang
# Expected output:
# NAME                       DESCRIPTION
# emsc-websocket-debug-noise  Exclude EMSC WebSocket high-frequency DEBUG messages
# httpx-debug-verbose         Exclude httpx DEBUG-level request/response logs
```

**สร้าง exclusion filters (ถ้ายังไม่มี — รัน setup script):**
```bash
export GCP_PROJECT=fonmayang
bash backend/scripts/setup_gcp.sh
```

**ตรวจสอบ log volume ลดลง:**
```bash
# ก่อน: EMSC messages จะเห็นทุก message
# หลัง: DEBUG messages ถูก exclude ออก
gcloud logging read 'severity=WARNING AND textPayload:"EMSC"' \
  --project=fonmayang \
  --limit=5
# Should see only reconnect/error events, NOT per-message noise
```

**ตรวจสอบ Python-level logging ทำงานถูกต้อง:**
```bash
# ดู log ขณะ server running — EMSC debug ต้องไม่ปรากฏ
# เฉพาะ earthquake event จริงๆ ถึงจะ log ที่ INFO level
gcloud logging read 'textPayload:"EMSC earthquake event"' \
  --project=fonmayang \
  --limit=5
```

---

### Checklist Issue #69 (Code Optimization) ✅

**Sub-task 1 — Dead URL Fix:**
- [ ] `kkn120` ไม่มี 404 loop GIF error ใน logs อีกต่อไป
- [ ] `kkn240` และ `skn240` ยัง fetch loop GIF ได้ปกติ

**Sub-task 2 — Async Parallel:**
- [ ] `fetch_tmd_radar_routine` log แสดง "complete: 3/3 stations"
- [ ] เวลา fetch รวมลดลงชัดเจนเทียบกับก่อนหน้า (เป้า < 15s)

**Sub-task 3 — Cloud Logging:**
- [ ] `gcloud logging exclusions list` แสดง 2 exclusions
- [ ] EMSC DEBUG noise ไม่ปรากฏใน Cloud Logging Viewer
- [ ] EMSC earthquake event จริงยังคง log ที่ INFO level

---

## Issue #72 — Budget Auto-shutdown Mechanism

### สถาปัตยกรรม

```
GCP Budget Alert
      │
      │ (at 80% → warning, at 100% → shutdown trigger)
      ▼
Pub/Sub Topic: billing-alerts
      │
      │ Push subscription
      ▼
POST /api/v1/internal/budget-alert (Cloud Run)
      │
      ├── 80% → ส่ง Telegram warning เท่านั้น
      └── 100% → gcloud run services update --max-instances=0
                  + ส่ง Telegram emergency alert
```

### ขั้นตอนตั้งค่า (ครั้งแรก)

1. **ตั้ง GitLab CI/CD Variables ใหม่ 2 ตัว:**
   - `GCP_BILLING_ACCOUNT_ID` = `XXXXXX-XXXXXX-XXXXXX` (หาได้จาก GCP Console → Billing)
   - `BUDGET_AMOUNT_USD` = `10` (หรือจำนวนที่ต้องการ)

2. **รัน setup script โดยตรง (ครั้งแรก):**
   ```bash
   export GCP_PROJECT_ID=fonmayang
   export GCP_BILLING_ACCOUNT_ID=XXXXXX-XXXXXX-XXXXXX
   export BUDGET_AMOUNT_USD=10
   cd backend
   bash scripts/setup_budget_alert.sh
   ```

3. **ตรวจสอบใน GCP Console:**
   - Billing → Budgets & Alerts → ตรวจว่ามี `fontokmai-api-monthly-budget` แล้ว
   - Pub/Sub → Topics → ตรวจว่ามี `billing-alerts` topic
   - Pub/Sub → Subscriptions → ตรวจว่า push endpoint ชี้ไปที่ Cloud Run URL ถูกต้อง

### ทดสอบ Endpoint โดยตรง

```bash
# สร้าง mock Pub/Sub payload สำหรับ 100% budget exceeded
MOCK_DATA=$(echo '{
  "budgetDisplayName": "fontokmai-api-monthly-budget",
  "alertThresholdExceeded": 1.0,
  "costAmount": 10.5,
  "budgetAmount": 10.0,
  "currencyCode": "USD"
}' | base64)

curl -s -X POST https://<CLOUD_RUN_URL>/api/v1/internal/budget-alert \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": {
      \"data\": \"$MOCK_DATA\",
      \"messageId\": \"test-123\",
      \"publishTime\": \"2026-06-16T10:00:00Z\"
    },
    \"subscription\": \"projects/fonmayang/subscriptions/billing-alerts-sub\"
  }"
```

**ผลลัพธ์ที่ต้องการ:**
```json
{"status": "shutdown_success", "cost": 10.5, "budget": 10.0}
```

### ทดสอบ 80% Warning

```bash
MOCK_DATA=$(echo '{
  "budgetDisplayName": "fontokmai-api-monthly-budget",
  "alertThresholdExceeded": 0.8,
  "costAmount": 8.0,
  "budgetAmount": 10.0,
  "currencyCode": "USD"
}' | base64)

curl -s -X POST https://<CLOUD_RUN_URL>/api/v1/internal/budget-alert \
  -H "Content-Type: application/json" \
  -d "{\"message\": {\"data\": \"$MOCK_DATA\", \"messageId\": \"warn-456\"}}"
```

**ผลลัพธ์ที่ต้องการ:**
```json
{"status": "warning_sent", "threshold": 0.8}
```

### Restore Cloud Run (หลังจาก shutdown)

ถ้าระบบปิดตัวเองเพราะ budget exceeded เราสามารถดึงกลับมาออนไลน์ (รับ public traffic) ได้โดยการรันคำสั่ง:
```bash
gcloud run services add-iam-policy-binding fontokmai-api \
  --region asia-southeast1 \
  --member "allUsers" \
  --role "roles/run.invoker"
```

### Checklist ✅

- [ ] `setup_budget_alert.sh` รันสำเร็จ
- [ ] Budget ปรากฏใน GCP Console
- [ ] Pub/Sub topic `billing-alerts` ถูกสร้าง
- [ ] Push subscription ชี้ไปที่ Cloud Run URL ถูกต้อง
- [ ] ทดสอบ mock 80% → ได้รับ Telegram warning
- [ ] ทดสอบ mock 100% → Cloud Run ถูกระงับสิทธิ์ public access
- [ ] ทดสอบ mock 100% → ได้รับ Telegram emergency alert
- [ ] Restore Cloud Run โดยการคืนสิทธิ์ allUsers

---

## Part 3: Verify Cloud Run Parameter Tuning & CI/CD Pipeline (from manual_verification2.md)

### Verify Cloud Run Parameters

- **Step 1:** Run the following command to check the deployed Cloud Run service configuration:
  ```bash
  gcloud run services describe fontokmai-api \
    --region asia-southeast1 \
    --format json | jq '{memory: .spec.template.spec.containers[0].resources.limits.memory, concurrency: .spec.containerConcurrency, timeout: .spec.template.spec.timeoutSeconds}'
  ```
- **Expected Result:** The output should display `memory: "512Mi"`, `concurrency: 40`, and `timeout: 120s`.

- **Step 2:** Perform a basic load test using a tool like `hey` to ensure the new concurrency limit of 40 handles requests smoothly:
  ```bash
  hey -n 100 -c 20 https://<CLOUD_RUN_URL>/health
  ```
- **Expected Result:** The test completes successfully with a 200 OK status for all requests, without returning 5xx errors or significant latency spikes.

- **Step 3:** Open the GCP Console and navigate to **Cloud Run -> Metrics -> Container Instance Count**.
- **Expected Result:** The maximum number of container instances running concurrently should not exceed 3.

### Verify Budget Alert CI/CD Pipeline Setup

- **Step 1:** Manually trigger the GitLab CI/CD pipeline or push a change to the `main` branch to trigger a deploy.
- **Expected Result:** The pipeline should reach the `deploy_cloud_run` stage.

- **Step 2:** Inspect the GitLab CI/CD logs for the `deploy_cloud_run` job.
- **Expected Result:** You should see the message "Setting up Budget Alert...". If `GCP_BILLING_ACCOUNT_ID` is set, the script `setup_budget_alert.sh` should execute successfully. If not set, it should output a warning "GCP_BILLING_ACCOUNT_ID not set. Skipping budget alert setup."

- **Step 3:** Open the GCP Console and navigate to **Billing -> Budgets & alerts**.
- **Expected Result:** The budget for the project (e.g., `fontokmai-api-monthly-budget`) should be present.

- **Step 4:** In the GCP Console, navigate to **Pub/Sub -> Topics**.
- **Expected Result:** The `billing-alerts` topic should exist.

- **Step 5:** Navigate to **Pub/Sub -> Subscriptions** and inspect the push subscription associated with `billing-alerts`.
- **Expected Result:** The push endpoint should correctly point to your Cloud Run URL (e.g., `https://<CLOUD_RUN_URL>/api/v1/internal/budget-alert`).

---

## Part 4: Local Testing Before Deployment 🛠️

คุณสามารถทดสอบฟังก์ชันต่างๆ ในเครื่อง Local ของคุณได้ก่อนที่จะพุชโค้ดขึ้นไปบน GitLab

### 1. ทดสอบ Webhook (Budget Auto-shutdown)
เนื่องจากเราทำ Webhook รับข้อมูลจาก Pub/Sub เราสามารถใช้ `curl` ยิงจำลอง (Mock) ข้อมูลเข้า Local Server ได้โดยตรง

**Step 1:** รันเซิร์ฟเวอร์ Local (ถ้ายังไม่ได้รัน)
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Step 2:** เปิด Terminal ใหม่ แล้วยิง cURL จำลองเหตุการณ์ **"เงินถึง 80%" (Warning)**
```bash
curl -X POST http://localhost:8000/api/v1/internal/budget-alert \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "data": "eyJidWRnZXREaXNwbGF5TmFtZSI6ImZvbnRva21haS1hcGktbW9udGhseS1idWRnZXQiLCJjb3N0QW1vdW50Ijo4LCJjb3N0SW50ZXJ2YWxTdGFydCI6IjIwMjQtMTAtMDFUMDc6MDA6MDBaIiwiYnVkZ2V0QW1vdW50IjoxMCwiYnVkZ2V0QW1vdW50VHlwZSI6IlNQRUNJRklFRF9BTU9VTlQiLCJjdXJyZW5jeUNvZGUiOiJUSEIifQ=="
    }
  }'
```
> **คำอธิบาย:** ข้อมูล `data` ข้างต้นคือ Base64 ของ JSON ที่บอกว่า Cost=8, Budget=10 (80%) ในสกุลเงิน THB
> **ผลลัพธ์ที่คาดหวัง:** คุณจะได้รับข้อความแจ้งเตือน **"⚠️ ⚠️ [WARNING] ⚠️ ⚠️ ค่าใช้จ่าย GCP ทะลุ 80% แล้ว!"** ใน Telegram ของคุณ

**Step 3:** ยิง cURL จำลองเหตุการณ์ **"เงินถึง 100%" (Shutdown Trigger)**
```bash
curl -X POST http://localhost:8000/api/v1/internal/budget-alert \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "data": "eyJidWRnZXREaXNwbGF5TmFtZSI6ImZvbnRva21haS1hcGktbW9udGhseS1idWRnZXQiLCJjb3N0QW1vdW50IjoxMSwiY29zdEludGVydmFsU3RhcnQiOiIyMDI0LTEwLTAxVDA3OjAwOjAwWiIsImJ1ZGdldEFtb3VudCI6MTAsImJ1ZGdldEFtb3VudFR5cGUiOiJTUEVDSUZJRURfQU1PVU5UIiwiY3VycmVuY3lDb2RlIjoiVEhCIn0="
    }
  }'
```
> **คำอธิบาย:** ข้อมูล `data` คือ Base64 ของ JSON ที่บอกว่า Cost=11, Budget=10 (> 100%) ในสกุลเงิน THB
> **ผลลัพธ์ที่คาดหวัง:** 
> 1. คุณจะได้รับข้อความแจ้งเตือน **"🚨 🚨 [EMERGENCY SHUTDOWN] 🚨 🚨"** ใน Telegram
> 2. ใน Console Log ของ Uvicorn จะมี error/log พยายามรันคำสั่ง `gcloud run services remove-iam-policy-binding` (ใน Local อาจจะไม่สำเร็จ เพราะไม่มีสิทธิ์ gcloud แต่เป็นการพิสูจน์ว่า Webhook ทำงานและแตกกิ่งได้ถูกต้อง)

### 2. ทดสอบสคริปต์สร้าง Budget Alert บน GCP
สคริปต์นี้เขียนด้วย `gcloud` CLI ล้วนๆ จึงสามารถรันจากเครื่อง Local ได้เลยเพื่อสร้าง Budget ล่วงหน้าโดยไม่ต้องรอ CI/CD (One-time Setup)

**Step 1:** ตรวจสอบและตั้งค่า Billing Account ID
```bash
export GCP_BILLING_ACCOUNT_ID="ใส่-BILLING-ID-ของคุณ"
export BUDGET_AMOUNT_THB="10"
```

**Step 2:** รันสคริปต์
```bash
bash backend/scripts/setup_budget_alert.sh
```
> **ผลลัพธ์ที่คาดหวัง:** สคริปต์จะวิ่งทำงานตั้งแต่ Step 1 - Step 6 และหากสำเร็จ ปลายทางคุณจะเห็น Topic `billing-alerts` และ Budget ปรากฏในหน้า GCP Console

### 3. ทดสอบ Async Parallel (ความเร็วการดูดรูปเรดาร์)
ฟังก์ชันนี้ไม่ต้องทำผ่าน cURL แต่รันโค้ด Python ได้ตรงๆ

**Step 1:** สร้างไฟล์สั้นๆ ในโฟลเดอร์ `backend/` ชื่อ `test_radar.py`
```python
import asyncio
from app.scheduler_tasks import fetch_tmd_radar_routine

async def test():
    print("Starting parallel fetch...")
    await fetch_tmd_radar_routine()
    print("Done!")

asyncio.run(test())
```

**Step 2:** สั่งรันจาก Terminal
```bash
cd backend
python test_radar.py
```
> **ผลลัพธ์ที่คาดหวัง:** โค้ดจะแสดง log การดึงข้อมูล `kkn120`, `kkn240`, `skn240` โดยจะเห็นว่าทั้ง 3 สถานีพยายามเริ่มทำงานในเวลาใกล้เคียงกัน (พร้อมกัน) สังเกตจากเวลาทำงานรวม (Execution Time) จะลดลง

### 4. ทดสอบ Cloud Logging Exclusions
เช่นเดียวกับสคริปต์ Budget คุณสามารถสั่งรันสคริปต์ Setup GCP ซ้ำในเครื่องคุณเพื่อสร้าง Filter รอไว้ก่อน Deploy โค้ด

**Step 1:** รันสคริปต์
```bash
bash backend/scripts/setup_gcp.sh
```
> **ผลลัพธ์ที่คาดหวัง:** สคริปต์จะแสดงข้อความว่า `Exclusion 'emsc-websocket-debug-noise' created/updated` และไปปรากฏในหน้า **Logging -> Logs Router** ใน GCP Console
