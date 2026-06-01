- Step 1: Start the FastAPI local server. Ensure your `.env` file is loaded if you have custom `CRON_SECRET` set, otherwise it defaults to `default_secret_for_local_testing`.
  ```bash
  uvicorn app.main:app --reload --port 8001
  ```
- Step 2: Open a new terminal and test the endpoint without the required authentication header using `curl`.
  ```bash
  curl -X POST http://localhost:8001/api/v1/cron/check-rain
  ```
- **Actual Result:** `{"detail":"Unauthorized"}`
- Step 3: Send a POST request with an incorrect authentication header.
  ```bash
  curl -X POST http://localhost:8001/api/v1/cron/check-rain -H "X-Cron-Secret: wrong_secret"
  ```
- **Actual Result:** `{"detail":"Unauthorized"}`
- Step 4: Send a POST request with the correct authentication header.
  ```bash
  curl -X POST http://localhost:8001/api/v1/cron/check-rain -H "X-Cron-Secret: default_secret_for_local_testing"
  ```
- **Actual Result:** `{"status":"ok","message":"Rain check task added to background"}`

**Conclusion:** All manual verification tests passed successfully, matching the expected behavior.
