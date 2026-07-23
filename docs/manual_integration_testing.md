# 🧪 Manual & Automated Integration Testing Guide (FonMaYang API)

เอกสารแนะนำวิธีการทดสอบ **Integration Testing** สำหรับระบบ FonMaYang ทั้งแบบอัตโนมัติด้วย Newman (Postman CLI) และแบบ Manual Integration

---

## 🚀 1. Automated Integration Test via Newman (CI/CD)

คุณสามารถสั่งรัน Integration Test ครบทุก API Endpoint ได้ทันทีใน Terminal ด้วยสคริปต์ Newman:

```bash
# 1. รัน Backend API ใน Terminal แรก
cd backend && uv run uvicorn app.main:app --port 8000

# 2. รัน Newman Integration Tests ใน Terminal ที่สอง
./scripts/run_newman_tests.sh
```

### 📊 รายงานผลลัพธ์ที่จะได้รับ:
* **Terminal Summary Table**: แสดงผลจำนวน API Assertions ที่ผ่าน (Passed / Failed)
* **JUnit XML Report**: สรุปผลสำหรับ GitLab CI Test Panel ที่ `./results/newman-junit.xml`
* **HTML Extra Visual Report**: หน้าเว็บรายงานผลการทดสอบแบบสวยงามที่ `./results/newman-report.html`

---

## 🛠️ 2. Manual Integration Testing Guide (ทุกกรณีการใช้งาน)

### Case 1: Live Runway Engine API (`GET /api/runway`)
* **วัตถุประสงค์**: ตรวจสอบการคำนวณวันคงเหลือของเซิร์ฟเวอร์ และการแบ่งโถงบประมาณ 3 โถ (50/30/20)
* **วิธีทดสอบ Manual**:
  ```bash
  curl -X GET http://localhost:8000/api/runway
  ```
* **ผลลัพธ์ที่คาดหวัง**:
  * HTTP Status: `200 OK`
  * JSON Response มี `days_remaining`, `total_balance_thb`, และ `budget_jars` ครบทั้ง 3 โถ

---

### Case 2: Milestone Progress & Donation Lock Kill-Switch (`GET /api/milestones`)
* **วัตถุประสงค์**: ตรวจสอบสถานะการล็อกการรับบริจาคเมื่อถึงเป้าหมาย Milestone
* **วิธีทดสอบ Manual**:
  1. สลับล็อกการรับบริจาค:
     ```bash
     python set_milestone_lock.py true
     ```
  2. ยิง API เช็คสถานะ:
     ```bash
     curl -X GET http://localhost:8000/api/milestones
     ```
* **ผลลัพธ์ที่คาดหวัง**:
  * `is_locked` ต้องส่งค่า `true`
  * `current_thb` และ `target_thb` ขยับเต็ม 10,000 THB (100%)
  * `lock_reason` แสดงข้อความแจ้งเตือนเป้าหมายสำเร็จ

---

### Case 3: Anonymous Magic Auth Token Generation (`POST /auth/generate-token`)
* **วัตถุประสงค์**: สร้างสิทธิ์ผู้ใช้และ Recovery Key แบบไม่เก็บข้อมูลส่วนบุคคล (Zero-PII)
* **วิธีทดสอบ Manual**:
  ```bash
  curl -X POST http://localhost:8000/auth/generate-token \
    -H "Content-Type: application/json" \
    -d '{
      "transaction_id": "tx_manual_test_999",
      "amount": 500.0,
      "timestamp": "2026-07-23T12:00:00Z"
    }'
  ```
* **ผลลัพธ์ที่คาดหวัง**:
  * HTTP Status: `200 OK`
  * JSON Response มี `token` รูปแบบ `Fon-XXXX-XXXX`

---

### Case 4: Zero-PII Stripe Webhook Listener (`POST /api/webhooks/stripe`)
* **วัตถุประสงค์**: รองรับการแจ้งเตือนยอดบริจาคจาก Stripe โดยไม่ต้องระบุ PII
* **วิธีทดสอบ Manual**:
  ```bash
  curl -X POST http://localhost:8000/api/webhooks/stripe \
    -H "Content-Type: application/json" \
    -H "Stripe-Signature: t=1721660000,v1=test_sig" \
    -d '{
      "id": "evt_test_123",
      "type": "checkout.session.completed",
      "data": {
        "object": {
          "id": "cs_test_session_123",
          "amount_total": 1000,
          "currency": "thb"
        }
      }
    }'
  ```
* **ผลลัพธ์ที่คาดหวัง**:
  * ตอบกลับด้วย Signature Verification Status (200 หรือ 400 ขึ้นอยู่กับความถูกต้องของ Stripe Key)

---

## 🔄 3. CI/CD Pipeline Integration (.gitlab-ci.yml)

ไฟล์ `.gitlab-ci.yml` ถูกกำหนดให้รัน `newman_api_integration_tests` อัตโนมัติทุกครั้งเมื่อมีการเปิด **Merge Request (MR)** หรือ Push ไปที่สาขา `main` โดยจะรัน Postman Collection และส่งรายงานผลการทดสอบไปยัง Telegram และ GitLab CI UI โดยตรง
