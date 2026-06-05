### Manual Verification Guide: Open-Meteo Integration

**Test 1: Verify API Comparison Endpoint**
- **Step 1:** Start your local FastAPI backend server (e.g., `uvicorn app.main:app --reload`).
- **Step 2:** Open a terminal or Postman and send a GET request to the comparison endpoint, for example: `curl "http://localhost:8000/api/v1/weather/compare?lat=13.7563&lng=100.5018"` (adjust path/query according to your router).
- **Expected Result:** The JSON response should contain a dictionary of results from multiple providers, and you should see an `"open-meteo"` key in the result containing its respective weather prediction data (`predictions`, `max_rain`, etc.).

**Test 2: Verify Open-Meteo Contingency (Fallback)**
- **Step 1:** While the server is running, temporarily disable the `XweatherService` (e.g., change `XWEATHER_ENABLED=false` in `.env` or provide an invalid `XWEATHER_CLIENT_ID` to force an exception).
- **Step 2:** Restart the server if necessary, then trigger a request that calls `get_advanced_alerts` (e.g., via the disaster webhook or directly via an exposed weather endpoint that returns advanced alerts).
- **Expected Result:** The server logs should output a warning: `Failed to fetch advanced alerts from Xweather: [...]. Falling back to Open-Meteo for wind vectors.` The returned `stormcell` object should have `distance_km: null`, `max_dbz: null`, but it **should** contain a valid `direction` (e.g., "SW") and `speed_kmh` (e.g., 15.5) derived from Open-Meteo.

**Test 3: Verify Open-Meteo Mock State**
- **Step 1:** Using `curl` or Postman, send a request to your API that triggers the `compare_all_apis` or `get_advanced_alerts` and pass a parameter to activate `mock_state="rain"`.
- **Expected Result:** The `open-meteo` response within the comparison should return exactly `max_rain: 15.0` and `intensity: "หนัก (Heavy)"`. For the wind vector contingency, it should return `direction: "E"` and `speed_kmh: 40.0`.
