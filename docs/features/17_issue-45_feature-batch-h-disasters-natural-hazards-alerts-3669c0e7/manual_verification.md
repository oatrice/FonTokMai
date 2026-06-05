# Manual Verification Guide

Here is a step-by-step guide to verify the Disaster Alerts implementation locally.

### Prerequisites
1. Ensure your local virtual environment is active: `source venv/bin/activate`
2. Run database migrations to ensure the `DisasterAlertHistory` table exists (if using Alembic: `alembic upgrade head`, or let `main.py` create it automatically on startup).
3. Start the FastAPI server locally: `uvicorn app.main:app --reload --port 8000`
4. Make sure you have valid user locations in your local database with your Telegram `chat_id`.

### Test 1: Verify Endpoint Authorization
- **Step 1:** Use `curl` to hit the new scheduler endpoint without a secret.
  ```bash
  curl -X POST http://localhost:8000/api/v1/cron/check-disasters-infrequent
  ```
- **Expected Result:** The API returns `HTTP 401 Unauthorized`.

### Test 2: Trigger Infrequent Disasters (Cyclones & Fires)
- **Step 1:** Trigger the infrequent disaster check with the correct cron secret.
  ```bash
  curl -X POST -H "X-Cron-Secret: default_secret_for_local_testing" http://localhost:8000/api/v1/cron/check-disasters-infrequent
  ```
- **Expected Result:** The endpoint should return `{"status": "ok", "message": "Infrequent disaster check task added to background"}`. Check your FastAPI logs. If there are active cyclones or fires near your database locations (e.g. within 500km for cyclones, 50km for fires), you should receive a Telegram message. Check the database to see the record in `DisasterAlertHistory`.

### Test 3: Trigger Frequent Disasters (USGS Earthquakes)
- **Step 1:** Trigger the frequent disaster check.
  ```bash
  curl -X POST -H "X-Cron-Secret: default_secret_for_local_testing" http://localhost:8000/api/v1/cron/check-disasters-frequent
  ```
- **Expected Result:** The endpoint returns status "ok". Check the terminal logs to see if USGS GeoJSON was fetched successfully. If any earthquakes match your radius (e.g. mag >= 4.5 within 100km, or mag >= 6.0 within 300km), you should get a Telegram alert.

### Test 4: Prevent Duplicate Alerts
- **Step 1:** Run Test 2 or Test 3 multiple times.
  ```bash
  curl -X POST -H "X-Cron-Secret: default_secret_for_local_testing" http://localhost:8000/api/v1/cron/check-disasters-frequent
  ```
- **Expected Result:** You should only receive the Telegram alert on the *first* trigger for a specific disaster ID. Subsequent runs should not send any duplicate Telegram messages, as they will be filtered by `DisasterAlertHistory` and the logs should not show any new alert events for those IDs.

### Test 5: Verify EMSC WebSocket (Real-time)
- **Step 1:** Observe the terminal startup logs of your running FastAPI server.
- **Expected Result:** You should see the log `Starting EMSC Earthquake WebSocket listener...` and then `Connected to EMSC WebSocket.`. The connection should remain open. Wait for a few minutes (or simulate a WebSocket message) to see if the background task successfully processes incoming earthquakes.
