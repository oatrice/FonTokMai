# Manual Verification — Issue #210: Stripe Auto Payout Webhook & Balance Reconciliation

## Overview
ตรวจสอบว่า `payout.created`, `payout.paid`, และ `payout.failed` events จาก Stripe ถูก handle อย่างถูกต้อง พร้อม idempotency และ audit trail ใน `payouts` table

---

## Prerequisites

```bash
# 1. ติดตั้ง Stripe CLI
brew install stripe/stripe-cli/stripe

# 2. Login กับ Stripe CLI
stripe login

# 3. เริ่ม webhook listener (forwarding ไปยัง local backend)
stripe listen --forward-to localhost:8000/api/webhooks/stripe
```

```bash
# 4. เริ่ม backend
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload
```

---

## Happy Path Tests

### Test 1: payout.created

```bash
stripe trigger payout.created
# Expected Logs:
# [STRIPE] Handled payout.created for payout po_xxx
# [PAYOUT] Recorded payout.created: po_xxx amount=500000
```

**ตรวจสอบใน DB:**
```bash
sqlite3 backend/fonmayang.db \
  "SELECT payout_id, status, amount_cents, idempotency_key FROM payouts LIMIT 5;"
# Expected: row ปรากฏขึ้นพร้อม status='pending'
```

### Test 2: Idempotency (ส่ง event ซ้ำ)

```bash
stripe trigger payout.created
# Expected Logs:
# [PAYOUT] Duplicate payout.created for po_xxx — skipping.
```

```bash
sqlite3 backend/fonmayang.db "SELECT COUNT(*) FROM payouts;"
# Expected: count ไม่เพิ่มขึ้น
```

### Test 3: payout.paid

```bash
stripe trigger payout.paid
# Expected: status='paid' ใน DB
```

### Test 4: payout.failed

```bash
stripe trigger payout.failed
# Expected: status='failed', failure_code และ failure_message ปรากฏใน DB
```

---

## Edge Case Tests

### Test 5: Invalid Signature (Security)

```bash
curl -X POST http://localhost:8000/api/webhooks/stripe \
  -H "Content-Type: application/json" \
  -H "Stripe-Signature: invalid_sig" \
  -d '{"type": "payout.created"}'
# Expected: HTTP 400 {"detail": "Invalid signature"}
```

---

## Automated Test Results

```bash
cd backend && source .venv/bin/activate && pytest tests/test_stripe_payout_webhook.py -v
# Expected: 13 passed ✅
```

---

## Zero-PII Verification

```bash
sqlite3 backend/fonmayang.db ".schema payouts"
# Expected columns: id, payout_id, status, amount_cents, currency, arrival_date,
#                   idempotency_key, failure_code, failure_message, created_at, updated_at
# NO columns: name, email, bank_account, iban, sort_code, phone
```
