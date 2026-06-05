- **Step 1:** Start the local backend server (e.g., `uvicorn app.main:app --reload`).
- **Step 2:** Open a separate terminal and trigger the new scheduler routine manually, or wait for the 15-minute interval to pass. Alternatively, you can test it via a Python interactive shell:
  ```python
  import asyncio
  from app.scheduler_tasks import fetch_tmd_radar_routine
  asyncio.run(fetch_tmd_radar_routine())
  ```
- **Expected Result (Step 2):** You should see logs in your backend terminal indicating "Starting TMD Radar fetch routine..." followed by "Successfully fetched latest radar image for kkn120" (and kkn240, skn120) with their respective byte sizes.
- **Step 3:** To test the `WeatherManager` integration, call the `predict_rain` method (or trigger the corresponding API endpoint) targeting a coordinate inside the Khon Kaen or Sakon Nakhon bounding box (e.g., Lat: 16.43, Lng: 102.83) with `force_endpoint="tmd-radar"` if applicable, or rely on the auto-fallback.
- **Expected Result (Step 3):** The response payload should include `"endpoint": "tmd-radar"` and return the stubbed dictionary (e.g., `intensity: "ไม่ทราบ"`, `max_rain: 0.0`) without throwing an "Out of bounds" exception.
- **Step 4:** Test with a coordinate far outside the TMD region (e.g., Bangkok: Lat: 13.75, Lng: 100.50).
- **Expected Result (Step 4):** The `_get_tmd_prediction` wrapper should raise the "Location out of bounds" exception internally, causing the `WeatherManager` fallback system to seamlessly skip it and move to the next available API (e.g., Open-Meteo).
