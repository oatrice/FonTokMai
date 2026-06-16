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

ถ้าระบบปิดตัวเองเพราะ budget exceeded สามารถ restore ได้:
```bash
gcloud run services update fontokmai-api \
  --region asia-southeast1 \
  --max-instances 3
```

### Checklist ✅

- [ ] `setup_budget_alert.sh` รันสำเร็จ
- [ ] Budget ปรากฏใน GCP Console
- [ ] Pub/Sub topic `billing-alerts` ถูกสร้าง
- [ ] Push subscription ชี้ไปที่ Cloud Run URL ถูกต้อง
- [ ] ทดสอบ mock 80% → ได้รับ Telegram warning
- [ ] ทดสอบ mock 100% → Cloud Run ถูก scale ลงเหลือ 0
- [ ] ทดสอบ mock 100% → ได้รับ Telegram emergency alert
- [ ] Restore Cloud Run กลับมา max-instances=3
