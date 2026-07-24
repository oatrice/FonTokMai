# Manual Verification — FonMaYang Financial Engine & Cost Transparency

## Issue #210: Stripe Auto Payout Webhook & Balance Reconciliation

### Overview
ตรวจสอบว่า `payout.created`, `payout.paid`, และ `payout.failed` events จาก Stripe ถูก handle อย่างถูกต้อง พร้อม idempotency และ audit trail ใน `payouts` table

---

### Prerequisites (Issue #210)

```bash
# 1. ติดตั้ง Stripe CLI
brew install stripe/stripe-cli/stripe

# 2. Login กับ Stripe CLI
stripe login

# 3. เริ่ม webhook listener (forwarding ไปยัง local backend)
stripe listen --forward-to localhost:8000/api/webhooks/stripe

# 4. เริ่ม backend
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload
```

---

### Verification Steps (Issue #210)

*หมายเหตุ: Stripe CLI `stripe trigger` ไม่รองรับ `payout.paid` / `payout.failed` โดยตรง และจำเป็นต้องผูก External Bank Account บน Stripe Dashboard ดังนั้นการทดสอบฝั่ง Local จึงใช้ Helper Script `backend/scripts/trigger_payout_webhook.py` ซึ่งคำนวณ Stripe Signature HMAC-SHA256 ให้อัตโนมัติ*

#### Test 1: payout.created (บันทึก Payout Record)

```bash
python backend/scripts/trigger_payout_webhook.py created
# Expected Output: Status: 200, Response: {"status":"success"}
```

**ตรวจสอบ DB:**
```bash
sqlite3 backend/fonmayang.db "SELECT payout_id, status, amount_cents, idempotency_key FROM payouts;"
# Expected: po_test_manual_123|pending|500000|po_test_manual_123-created
```

#### Test 2: Idempotency (ส่ง event ซ้ำ)

```bash
python backend/scripts/trigger_payout_webhook.py created
# Expected Logs (Backend): [PAYOUT] Duplicate payout.created for po_test_manual_123 — skipping.
```

**ตรวจสอบ DB:**
```bash
sqlite3 backend/fonmayang.db "SELECT COUNT(*) FROM payouts;"
# Expected: 1 (ไม่เกิด row ซ้ำ)
```

#### Test 3: payout.paid (อัปเดตสถานะสำเร็จ)

```bash
python backend/scripts/trigger_payout_webhook.py paid
# Expected Output: Status: 200, Response: {"status":"success"}
```

**ตรวจสอบ DB:**
```bash
sqlite3 backend/fonmayang.db "SELECT payout_id, status FROM payouts WHERE payout_id='po_test_manual_123';"
# Expected: po_test_manual_123|paid
```

#### Test 4: payout.failed (อัปเดตสถานะล้มเหลวพร้อมเหตุผล)

```bash
python backend/scripts/trigger_payout_webhook.py failed
# Expected Output: Status: 200, Response: {"status":"success"}
```

**ตรวจสอบ DB:**
```bash
sqlite3 backend/fonmayang.db "SELECT payout_id, status, failure_code, failure_message FROM payouts WHERE payout_id='po_test_manual_123';"
# Expected: po_test_manual_123|failed|account_closed|The bank account has been closed.
```

---

## Issue #211: GCP Cloud Billing API & Dashboard

### Overview
ตรวจสอบว่า `GCPBillingService`, API Endpoint `/api/v1/metrics/gcp-costs` และ Frontend Component `GCPCostBreakdown` ทำงานร่วมกันได้ถูกต้อง ทั้งในกรณีใช้ Mock Data (Dev/Staging) และข้อมูลจริงจาก GCP BigQuery

---

### Verification Steps (Issue #211)

#### Test 1: Backend Endpoint Auth Guard (401 Unauthorized)
```bash
# พยายามเข้าถึง endpoint โดยไม่มี x-cron-secret header
curl -i http://localhost:8000/api/v1/metrics/gcp-costs

# Expected Output:
# HTTP/1.1 401 Unauthorized
# {"detail":"Unauthorized"}
```

#### Test 2: Backend Endpoint Success (Mock Fallback)
```bash
# เรียกผ่าน x-cron-secret header (ใช้ secret เดียวกับ env)
CRON_SECRET=$(grep CRON_SECRET backend/.env | cut -d '=' -f2)
curl -i -H "x-cron-secret: ${CRON_SECRET}" http://localhost:8000/api/v1/metrics/gcp-costs

# Expected Response (200 OK):
# {
#   "cloud_run_usd": 8.4,
#   "cloud_storage_usd": 1.2,
#   "egress_usd": 0.6,
#   "other_usd": 0.8,
#   "total_usd": 11.0,
#   "period_start": "2026-07-01",
#   "period_end": "2026-07-24",
#   "currency": "USD",
#   "is_mock": true
# }
```

#### Test 3: Next.js API Proxy Route Verification
```bash
# สตาร์ท frontend และเรียกผ่าน Next.js route (proxy จะแนบ CRON_SECRET ให้อัตโนมัติ)
curl -i http://localhost:3000/api/metrics/gcp-costs

# Expected Response (200 OK):
# ส่งกลับ JSON payload เดียวกับ Backend endpoint โดยไม่เปิดเผย CRON_SECRET สู่ Client
```

#### Test 4: Frontend UI Verification (GCPCostBreakdown Component)
1. เปิด Web Browser ไปที่ Dashboard (`http://localhost:3000`)
2. สังเกต Component **GCP Infrastructure Costs**:
   - **Total Display**: แสดงผล `$11.00 USD / month`
   - **Badge**: ขึ้นป้ายกำกับ Amber `Mock Data` เมื่อ `is_mock = true`
   - **Service Rows & Progress Bars**:
     - Cloud Run: `$8.40` (76%)
     - Cloud Storage: `$1.20` (11%)
     - Network Egress: `$0.60` (5%)
     - Other Services: `$0.80` (7%)
3. คลิกปุ่ม **Refresh** (ไอคอนวงกลมหมุน):
   - ปุ่มแสดง Spinner และดึงข้อมูลใหม่จาก `/api/metrics/gcp-costs` สำเร็จ

---

## Automated Test Execution Summary

```bash
cd backend && source .venv/bin/activate
pytest tests/test_stripe_payout_webhook.py tests/test_gcp_billing.py -v
```

**Results:**
- `test_stripe_payout_webhook.py`: **13 passed** ✅
- `test_gcp_billing.py`: **8 passed** ✅
- Full Suite Regression: **294 passed, 4 skipped** ✅
>>>>>>> feat/210-stripe-payout-webhook
