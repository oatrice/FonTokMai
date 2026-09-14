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

## 📸 Proof of Verification (Artifacts & Logs)
- **Automated Verification Summary**:
  - `pytest backend/tests/test_dashboard_metrics.py -v` result: `1 passed`
  - All automated Unit Economic logic verified correctly, accurately filtering mock rows and computing correct blended cost rates.
