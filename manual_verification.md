# Manual Verification: Pause Google Cloud Scheduler Jobs on Budget Exceed

## Feature Scope
- **Issue:** #286 (`Pause Google Cloud Scheduler jobs upon budget limit exceeded`)
- **Components Modified:**
  - `backend/app/routers/budget_webhook.py`: Pauses all managed Cloud Scheduler jobs via GCP API when budget threshold >= 100% (or ratio >= 1.0) along with revoking Cloud Run public access.
  - `backend/app/routers/webhook_admin.py`: Resumes active Cloud Scheduler jobs when admin executes `/restore_public_access`.
  - `VERSION`, `backend/VERSION`, `CHANGELOG.md`: Version incremented to `0.73.3`.

---

## Prerequisites
1. Ensure the Python environment is set up and required packages are installed (`pytest`, `respx`, etc.).
2. For real GCP manual verification, ensure `gcloud` is authenticated with permissions on Cloud Scheduler and Cloud Run in project `fonmayang`.

---

## Automated Verification

Run all targeted unit and integration tests:
```bash
pytest backend/tests/test_budget_webhook.py backend/tests/test_developer_commands.py
```
**Expected Result:**
All 16 tests pass without errors.

Verify environment sync check:
```bash
pytest backend/tests/test_deploy_env_sync.py
```
**Expected Result:**
1 passed.

---

## Manual Verification Steps

### Step 1: Simulate Budget Exceeded (100%) Webhook
Send a mock GCP Budget Alert Pub/Sub push notification simulating 100% threshold:
```bash
curl -X POST http://localhost:8000/api/v1/internal/budget-alert \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "data": "'$(echo -n '{"budgetDisplayName":"Prod Budget","alertThresholdExceeded":1.0,"costAmount":10.0,"budgetAmount":10.0,"currencyCode":"USD"}' | base64)'",
      "messageId": "manual-test-100"
    }
  }'
```
**Expected Behavior:**
1. Response HTTP 200 `{"status": "shutdown_success", "cost": 10.0, "budget": 10.0}`.
2. Server log confirms:
   - `[BudgetAlert] 🚨 Budget 100% exceeded! Initiating Cloud Run shutdown...`
   - `[BudgetAlert] ⏸️ Paused Cloud Scheduler job: ...` for each managed job in `schedulers.json`.
   - Telegram notification alert sent with Cloud Scheduler paused summary.

### Step 2: Service Restoration Workflow
Send `/restore_public_access` command via developer Telegram bot or admin handler:
```bash
# In Telegram chat with developer bot:
/restore_public_access
```
**Expected Behavior:**
1. `emergency_shutdown` flag resets to `False` in DB.
2. Server log confirms:
   - `[restore_public_access] ▶️ Resumed Cloud Scheduler job: ...` for active jobs (`fonmayang-check-rain`, `fonmayang-fetch-radar`, `fonmayang-sync-burn-rate`), skipping permanently paused jobs.
3. Bot replies confirming public access restoration and scheduler resumption.
