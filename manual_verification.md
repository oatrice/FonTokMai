# Manual Verification Plan - Location Management, Presence Verification & Cost Dashboard (MR 1, 2, 3)

- **Batches Covered**:
  - **MR 1 (!97)**: `feat/287-288-location-crud-snooze` (Issues #287, #288)
  - **MR 2 (!98)**: `feat/289-290-291-presence-check` (Issues #289, #290, #291)
  - **MR 3 (!99)**: `feat/292-296-dashboard-metrics` (Issues #292, #293, #294, #295, #296)
- **Target Integration Branch**: `dev`
- **Date**: 2026-09-14

---

## 📌 Prerequisites & Environment Setup

1. **Environment Variables**:
   Ensure `.env` or environment contains necessary variables for local testing:
   ```bash
   TELEGRAM_BOT_TOKEN="mock-test-token"
   ADMIN_CHAT_ID="12345678"
   DATABASE_URL="sqlite:///./test_fonmayang.db"
   ```

2. **Launch Local Backend**:
   ```bash
   poetry run uvicorn backend.app.main:app --reload --port 8000
   ```

3. **Launch Local Frontend (Web Admin)**:
   ```bash
   cd frontend && npm run dev
   ```
   Admin Portal runs at `http://localhost:3000/admin`.

---

## 🧪 Automated Test Verification

Run all test suites associated with the 3 MRs:
```bash
poetry run pytest backend/tests/test_location_crud.py \
                  backend/tests/test_webhook_location_commands.py \
                  backend/tests/test_presence_check.py \
                  backend/tests/test_dashboard_metrics.py \
                  backend/tests/test_deploy_env_sync.py -v
```
**Expected Outcome:**
- All 6 tests pass without error (`6 passed`).
- Environment variable sync test confirms all environment variables match deployment script.

---

## 🧪 Manual Verification Scenarios

---

### Batch 1 (MR 1): Location Name CRUD & Snooze Controls (#287, #288)

#### Scenario 1.1: Listing Locations & Snooze Status via Telegram
- **Goal**: Verify `/locations` command displays all registered user locations with status badges and mute buttons.
- **Steps**:
  1. In Telegram bot chat, send:
     ```text
     /locations
     ```
- **Expected Outcome**:
  - Bot responds with list of saved locations, e.g.:
    ```text
    📍 พิกัดที่คุณบันทึกไว้:
    • 🏠 บ้าน (Lat: 13.75, Lon: 100.50) [🟢 Active]
    ```
  - Inline keyboard options displayed below message:
    `[🔕 ปิด 1ชม.]` `[🔕 4ชม.]` `[🔕 24ชม.]` `[✅ เปิดเตือน]` `[⚙️ ตั้งค่าเตือน บ้าน]`

#### Scenario 1.2: Snoozing a Location & Filter from Rain Alerts
- **Goal**: Verify snoozing a location updates `is_snoozed=True`, sets `snooze_until`, and excludes it from `get_active_locations()`.
- **Steps**:
  1. Click inline button `[🔕 ปิด 1ชม.]` on location "บ้าน".
  2. Query database or send `/locations` again.
- **Expected Outcome**:
  - Bot sends Telegram alert/toast: `🔕 ปิดการแจ้งเตือน บ้าน ชั่วคราวเป็นเวลา 1 ชั่วโมงแล้ว`
  - `/locations` display updates badge to:
    ```text
    • 🏠 บ้าน [🔕 Snoozed (ถึง HH:MM)]
    ```
  - Rain checking worker excludes "บ้าน" from alert candidates during the snooze window.

#### Scenario 1.3: Renaming a Location
- **Goal**: Verify `/rename <old_name> <new_name>` properly updates the name in the database.
- **Steps**:
  1. In Telegram bot chat, send:
     ```text
     /rename บ้าน ที่ทำงานใหม่
     ```
- **Expected Outcome**:
  - Bot responds: `✅ เปลี่ยนชื่อพิกัดจาก 'บ้าน' เป็น 'ที่ทำงานใหม่' เรียบร้อยแล้ว`
  - Calling `/locations` shows `• ที่ทำงานใหม่ [🟢 Active]`.

---

### Batch 2 (MR 2): Presence Verification System & Flow (#289, #290, #291)

#### Scenario 2.1: Configuring Presence Policy & Countdown TTL
- **Goal**: Verify user can configure per-location presence mode (`always_ask`, `schedule_based`, `always_notify`).
- **Steps**:
  1. Send `/presence ที่ทำงานใหม่` or click `[⚙️ ตั้งค่าเตือน ที่ทำงานใหม่]`.
  2. Select policy mode `ถามก่อนเสมอ (Always Ask)`.
  3. Select cache TTL `จำคำตอบ 2 ชม.`.
- **Expected Outcome**:
  - Bot confirms policy configuration:
    ```text
    ✅ อัปเดตการตั้งค่าพิกัด ที่ทำงานใหม่:
    • นโยบาย: ถามก่อนเสมอ (Always Ask)
    • จดจำคำตอบ: 120 นาที
    • Timeout Fallback: ไม่ส่งเตือน (Silent)
    ```
  - `UserLocation` record in DB updates `presence_policy="always_ask"` and `presence_answer_ttl_minutes=120`.

#### Scenario 2.2: Interactive Presence Ping with Countdown TTL Cache
- **Goal**: When rain is detected near "ที่ทำงานใหม่", bot pings user asking if they are present. Selecting "อยู่ใกล้" or "ไม่ได้อยู่" caches answer for 2 hours.
- **Steps**:
  1. Trigger rain detection cycle for location set to `always_ask`.
  2. Bot sends interactive Presence Ping:
     ```text
     🌧️ ตรวจพบกลุ่มฝนใกล้พิกัด 'ที่ทำงานใหม่'!
     ตอนนี้คุณอยู่ใกล้บริเวณนี้หรือไม่?
     ```
     With buttons: `[📍 อยู่ใกล้ (ส่งเตือน)]` `[🚗 ไม่อยู่ (ไม่ต้องเตือน)]`
  3. Click `[🚗 ไม่อยู่ (ไม่ต้องเตือน)]`.
- **Expected Outcome**:
  - Bot edits message to: `บันทึกแล้ว: คุณไม่ได้อยู่ใกล้ 'ที่ทำงานใหม่' (จะจำคำตอบนี้ไว้ 120 นาที)`
  - Table `presence_answer_cache` stores `chat_id`, `location_name`, `answer="not_present"`, `expires_at = now + 2h`.
  - Next rain check within 2 hours skips notification without sending another ping.

---

### Batch 3 (MR 3): Accuracy Dashboard & Cost Breakdown (#292, #293, #294, #295, #296)

#### Scenario 3.1: REST API Telemetry & Cost Aggregation
- **Goal**: Verify `/api/v1/metrics/monthly` and `/api/v1/metrics/cost` return accurate calculations.
- **Steps**:
  1. Test Monthly Accuracy Metrics API:
     ```bash
     curl -s http://localhost:8000/api/v1/metrics/monthly?month=2026-09 | jq .
     ```
  2. Test Cost Breakdown API:
     ```bash
     curl -s http://localhost:8000/api/v1/metrics/cost?month=2026-09 | jq .
     ```
- **Expected Outcome**:
  - `GET /api/v1/metrics/monthly` returns:
    ```json
    {
      "month": "2026-09",
      "total_alerts": 142,
      "true_alarms": 128,
      "false_alarms": 14,
      "accuracy_rate": 90.14,
      "daily_breakdown": [...]
    }
    ```
  - `GET /api/v1/metrics/cost` returns combined GCP + External costs and calculated unit metrics:
    ```json
    {
      "month": "2026-09",
      "gcp_cost": 4.50,
      "external_cost": 1.20,
      "total_cost": 5.70,
      "cost_per_alert": 0.04,
      "cost_per_true_alert": 0.044
    }
    ```

#### Scenario 3.2: Telegram Admin `/stats` and `/cost` Commands
- **Goal**: Verify admin user can view accuracy and financial metrics directly in Telegram.
- **Steps**:
  1. From Admin Telegram account, send:
     ```text
     /stats 2026-09
     ```
  2. Send:
     ```text
     /cost 2026-09
     ```
- **Expected Outcome**:
  - `/stats` responds with formatted summary:
    ```text
    📊 สรุปความแม่นยำการแจ้งเตือน (2026-09)
    • แจ้งเตือนทั้งหมด: 142 ครั้ง
    • ฝนตกจริง (True Alarm): 128 ครั้ง
    • แจ้งเตือนพลาด (False Alarm): 14 ครั้ง
    • อัตราความแม่นยำ: 90.1%
    ```
  - `/cost` responds with operational cost breakdown:
    ```text
    💰 สรุปต้นทุนระบบ (2026-09)
    • ค่าบริการ GCP: $4.50
    • ค่าบริการภายนอก (API/Proxy): $1.20
    • ต้นทุนรวม: $5.70
    • เฉลี่ยต่อ Alert: $0.040
    • เฉลี่ยต่อ Alert ที่ตกจริง: $0.044
    ```

#### Scenario 3.3: Web Admin UI Portal
- **Goal**: Verify Web Admin dashboard renders charts, false alarm logs, and location policies.
- **Steps**:
  1. Open browser to `http://localhost:3000/admin/metrics`.
  2. Inspect Monthly Accuracy card, Accuracy Trend graph, and Cost per Alert metrics.
  3. Open browser to `http://localhost:3000/admin/locations`.
  4. Inspect location list, toggle snooze state, and adjust schedule active windows.
- **Expected Outcome**:
  - UI loads cleanly without console errors.
  - Recharts bar/line graphs accurately display monthly alert distribution.
  - Location settings panel allows quick schedule adjustments and policy changes.

---

## 📸 Proof of Verification (Artifacts & Logs)

### Automated Test Run Output
```text
============================= test session starts ==============================
collected 6 items

backend/tests/test_location_crud.py ..                                   [ 33%]
backend/tests/test_webhook_location_commands.py .                        [ 50%]
backend/tests/test_presence_check.py .                                   [ 66%]
backend/tests/test_dashboard_metrics.py .                                [ 83%]
backend/tests/test_deploy_env_sync.py .                                  [100%]

============================== 6 passed in 0.94s ===============================
```
