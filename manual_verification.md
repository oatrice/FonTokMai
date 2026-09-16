# Manual Verification Plan - Unified Event Log Economics & Admin Dashboard (Issues 298-301)

- **Branch**: `feat/298-301-unified-event-log-economics`
- **MR / Issue ID**: `#298, #299, #300, #301`
- **Date**: `2026-09-14`

---

## 📌 Prerequisites & Environment Setup
1. Ensure the PostgreSQL database is running.
2. Shell commands to launch server locally:
   ```bash
   cd backend
   poetry run uvicorn app.main:app --reload
   ```
3. Run the Next.js frontend:
   ```bash
   cd frontend
   npm run dev
   ```

---

## 🧪 Verification Scenarios

### Scenario 1: Verify SystemUsageEvent schema migration
- **Goal**: Verify that the table `alert_notification_log` has been successfully renamed to `system_usage_events` and the new columns have been added.
- **Steps**:
  1. Access the PostgreSQL shell: `psql -U postgres -d <your_db_name>`
  2. Run `\d system_usage_events`
- **Expected Outcome**:
  - Table exists.
  - Columns `event_category` (VARCHAR), `command_name` (VARCHAR), and `is_mock` (BOOLEAN) are present.

---

### Scenario 2: Verify On-Demand Query Logging (Telegram)
- **Goal**: Verify that `/compare_api` or `/check` logs into the system usage table.
- **Steps**:
  1. Send `/check` to the Telegram bot or trigger the Compare API inline button.
  2. Query the database: `SELECT * FROM system_usage_events ORDER BY id DESC LIMIT 1;`
- **Expected Outcome**:
  - A new row is inserted.
  - `event_category` is `ondemand_query`.
  - `command_name` is populated (e.g., `/check` or `compare_api`).
  - `is_mock` is `false`.

---

### Scenario 3: Verify Mock Rain Test is Excluded from Unit Economics
- **Goal**: Verify that mock triggers do not pollute accuracy and cost metrics.
- **Steps**:
  1. Send `/mock_rain` in Telegram.
  2. Check DB: `SELECT * FROM system_usage_events ORDER BY id DESC LIMIT 1;` -> `is_mock` should be `true`.
  3. Query `GET /api/v1/metrics/cost`
- **Expected Outcome**:
  - The mock alert is ignored in the `proactive_count`, `ondemand_count`, and cost per alert calculations.

---

### Scenario 4: Verify Admin Metrics Dashboard Frontend
- **Goal**: Verify the new UI fields reflect the multi-tier unit economics correctly.
- **Steps**:
  1. Open the frontend dashboard `http://localhost:3000/admin/metrics`.
  2. Select the current month.
- **Expected Outcome**:
  - Page renders without errors.
  - Cards show "Proactive Alerts", "On-Demand Queries", "Cost / Proactive Alert", "Cost / On-Demand Query", and "Blended Cost / User".

---

### Scenario 5: Verify Locations Admin Security & Filtering
- **Goal**: Verify that `/api/locations` requires `x-cron-secret` auth header, Next.js server-side proxies it safely, and the admin UI search filter operates smoothly.
- **Steps**:
  1. Curl backend directly without header: `curl -i http://localhost:8000/api/locations` -> Expect `401 Unauthorized`.
  2. Curl backend with header: `curl -i -H "x-cron-secret: <CRON_SECRET>" http://localhost:8000/api/locations` -> Expect `200 OK` with JSON array.
  3. Open frontend `http://localhost:3000/admin/locations` in browser.
  4. Type in the search input box (e.g. chat ID or location name).
- **Expected Outcome**:
  - Direct unauthenticated backend access is securely rejected.
  - Frontend admin table displays data seamlessly via server-side Next.js route handler.
  - Search filter dynamically filters rows in real time.

---

## 📸 Proof of Verification (Artifacts & Logs)
- **Automated Verification Summary**:
  - `pytest backend/tests/test_locations_endpoint.py -v`: Verified unauthenticated 401 rejection and authenticated 200 responses.
  - `pytest backend/tests` result: `537 passed, 4 skipped`
  - `npm run test` (Frontend Jest): `6 test suites passed, 40 tests passed`
  - `npm run build` (Next.js Production Build): Compiled with 0 errors across all 13 routes.

