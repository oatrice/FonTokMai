# Manual Verification Guide

Here is a step-by-step guide to verify the Disaster Alerts implementation locally.

### Prerequisites
1. Ensure your local virtual environment is active: `source venv/bin/activate`
2. Run database migrations or ensure the `DisasterAlertHistory` is supported by your chosen repository (Firestore or SQLite).
3. Start the FastAPI server locally: `uvicorn app.main:app --reload --port 8000`
4. Make sure you have valid user locations in your local database with your Telegram `chat_id`.

### Impact Radiuses
The system is configured to alert users if a disaster occurs within the following radiuses from their saved locations:
- **Earthquake >= 7.0:** 1,000 km
- **Earthquake 6.0 - 6.9:** 800 km
- **Earthquake 4.5 - 5.9:** 300 km
- **Cyclone:** 1,000 km
- **Fire:** 200 km

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
- **Expected Result:** The endpoint should return `{"status": "ok", "message": "Infrequent disaster check task added to background"}`. Check your FastAPI logs. If there are active cyclones or fires near your database locations (e.g. within 1,000km for cyclones, 200km for fires), you should receive a Telegram message. Check the database/Firestore to see the record in `disaster_alerts_history`.

### Test 3: Trigger Frequent Disasters (USGS Earthquakes)
- **Step 1:** Trigger the frequent disaster check.
  ```bash
  curl -X POST -H "X-Cron-Secret: default_secret_for_local_testing" http://localhost:8000/api/v1/cron/check-disasters-frequent
  ```
- **Expected Result:** The endpoint returns status "ok". Check the terminal logs to see if USGS GeoJSON was fetched successfully. If any earthquakes match your radius (e.g. mag >= 4.5 within 300km, or mag >= 7.0 within 1,000km), you should get a Telegram alert.

### Test 4: Prevent Duplicate Alerts
- **Step 1:** Run Test 2 or Test 3 multiple times.
  ```bash
  curl -X POST -H "X-Cron-Secret: default_secret_for_local_testing" http://localhost:8000/api/v1/cron/check-disasters-frequent
  ```
- **Expected Result:** You should only receive the Telegram alert on the *first* trigger for a specific disaster ID. Subsequent runs should not send any duplicate Telegram messages, as they will be filtered by `DisasterAlertHistory` and the logs should not show any new alert events for those IDs.

### Test 5: Verify EMSC WebSocket (Real-time)
- **Step 1:** Observe the terminal startup logs of your running FastAPI server. You should see `Connected to EMSC WebSocket.`
- **Step 2 (Wait & See):** You can leave the server running. When a small earthquake happens somewhere in the world, EMSC will push the data to your server and you will see it processed in the background.
- **Step 3 (Mock End-to-End WebSocket Test with Postman):**
  If you want to simulate an earthquake right now using a full End-to-End pipeline:
  1. Open a new terminal window in the `backend` folder and run the Hybrid Mock Server:
     ```bash
     source venv/bin/activate
     python mock_emsc_ws.py
     ```
     *(This runs a single script opening two ports: `8765` for WebSocket and `8766` for HTTP)*
  2. Stop your existing FastAPI server (`Ctrl+C`) and run it again, pointing to the mock server:
     ```bash
     EMSC_WS_URL=ws://localhost:8765 uvicorn app.main:app --reload --port 8001
     ```
  3. Open Postman and send a `POST` request to `http://localhost:8766/trigger` with this JSON body:
     ```json
     {
       "mag": 8.5,
       "lat": 13.75,
       "lng": 100.5,
       "place": "E2E Earthquake"
     }
     ```
  4. The mock server will receive the HTTP POST, convert it to an EMSC WebSocket payload, and push it to port `8765`. Your Uvicorn server will catch it, calculate the distance, and send a Telegram alert.

### Test 6: Mock All Disaster Alerts via CLI
- **Step 1:** Run the mock script to trigger a fake Earthquake, Cyclone, and Fire centered precisely on your active database location.
  ```bash
  source venv/bin/activate
  python mock_disasters.py
  ```
  *(You can also pass custom arguments like `--type cyclone --lat 13.75 --lng 100.5`)*
- **Expected Result:** You will receive 3 distinct Telegram messages (one for each disaster type) beautifully formatted.

### Test 7: Mock Disaster Alerts via FastAPI Backdoor (Postman)
- **Step 1:** If you don't want to use the CLI or WebSocket, you can trigger a mock alert directly through the FastAPI app. Send a `POST` request to `http://localhost:8001/api/v1/cron/trigger-mock-disaster`.
- **Headers Required:** 
  - `X-Cron-Secret: default_secret_for_local_testing`
- **Body (JSON):**
  ```json
  {
    "type": "cyclone",
    "lat": 13.75,
    "lng": 100.5,
    "name": "Postman Cyclone"
  }
  ```
- **Expected Result:** The backend will enqueue the mock disaster processing in the background and you will receive a Telegram message.
