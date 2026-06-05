### Manual Verification Guide: Open-Meteo Integration

**Test 1: Verify API Comparison Endpoint**
- **Step 1:** Start your local FastAPI backend server (e.g., `uvicorn app.main:app --reload`).
- **Step 2:** Open a terminal or Postman and send a GET request to the comparison endpoint, for example: `curl "http://localhost:8000/api/v1/weather/compare?lat=13.7563&lng=100.5018"` (adjust path/query according to your router).
- **Expected Result:** The JSON response should contain a dictionary of results from multiple providers, and you should see an `"open-meteo"` key in the result containing its respective weather prediction data (`predictions`, `max_rain`, etc.).

**Test 2: Verify Open-Meteo Contingency (Fallback)**
- **Step 1:** You can test the fallback directly without modifying `.env` by running this simple script in your terminal (at the project root):
  ```bash
  cd backend
  source venv/bin/activate  # Or your virtual environment
  python -c '
  import asyncio
  from app.services.weather_manager import WeatherManager

  async def test():
      wm = WeatherManager()
      # Force Xweather to fail
      wm.xweather_svc.enabled = False
      result = await wm.get_advanced_alerts(13.7563, 100.5018)
      print("Fallback Result:", result)

  asyncio.run(test())
  '
  ```
- **Expected Result:** The console should output `Fallback Result: {'advisories': [], 'lightning': None, 'stormcell': {'distance_km': None, 'direction': '...', 'speed_kmh': ..., 'max_dbz': None}}` where `direction` and `speed_kmh` are valid values fetched from Open-Meteo as a contingency.

**Test 3: Verify Open-Meteo Mock State**
- **Step 1:** You can verify the mock states by running this simple script in your terminal (at the project root):
  ```bash
  cd backend
  source venv/bin/activate  # Or your virtual environment
  python -c '
  import asyncio
  from app.services.open_meteo import OpenMeteoService

  async def test():
      svc = OpenMeteoService()
      
      print("--- Testing mock_state=\"rain\" ---")
      rain_res = await svc.predict_rain_by_location(13.7, 100.5, mock_state="rain")
      print("Max Rain:", rain_res.get("max_rain"))
      print("Intensity:", rain_res.get("intensity"))
      
      wind_res = await svc.get_wind_vector(13.7, 100.5, mock_state="rain")
      print("\nWind Direction:", wind_res.get("direction_cardinal"))
      print("Wind Speed (km/h):", wind_res.get("speed_kmh"))

  asyncio.run(test())
  '
  ```
- **Expected Result:** The console should exactly print `Max Rain: 15.0`, `Intensity: หนัก (Heavy)`, `Wind Direction: E`, and `Wind Speed (km/h): 40.0`.

**Test 4: E2E Telegram Verification (Issue #48 & #49)**
- **Step 1:** Start your FastAPI server with Xweather disabled to trigger the fallback:
  ```bash
  XWEATHER_ENABLED=false uvicorn app.main:app --host 127.0.0.1 --port 8000
  ```
- **Step 2:** Ensure your webhook is connected (e.g. via `localtunnel` or `ngrok` matching your Telegram bot webhook URL).
- **Step 3:** Open your Telegram app, go to your bot, and type:
  ```text
  /devmock rain
  ```
- **Expected Result (Issue #48):** The bot will immediately send a simulated heavy rain alert. In the second message block (ข้อมูลเตือนภัยขั้นสูง), you should see it output:
  ```text
  🌪️ แนวโน้มกลุ่มฝน/ลม (Contingency):
     - ทิศทาง: E
     - ความเร็วลม: 40.0 km/h

  ℹ️ ข้อมูลขั้นสูงจาก Open-Meteo (Fallback)
  ```
- **Step 4 (Issue #49):** Look at the inline keyboard buttons attached to the first alert message. Click the **"📊 เทียบข้อมูล"** (Compare API) button.
- **Expected Result (Issue #49):** The bot will edit the message to display a complete comparison of all APIs (Tomorrow.io, Rainbow, Open-Meteo, Xweather) natively inside the Telegram chat, showing `max_rain`, `intensity`, and `wind_speed_kmh` from Open-Meteo properly integrated into the comparison view.

**Test 5: Verify API Accuracy Evaluation (False Alarm & Auto-Sort Fallback)**
- **Step 1:** Start your FastAPI server (e.g., `uvicorn app.main:app --host 127.0.0.1 --port 8000`) and ensure your Telegram Webhook is connected.
- **Step 2:** Open your Telegram app, go to your bot, and type:
  ```text
  /devmock rain
  ```
- **Step 3:** The bot will send a simulated rain alert. Beneath the alert message, you will see an inline button labeled **"❌ แจ้งเตือนผิดพลาด"** (False Alarm). Click it.
- **Step 4:** The bot should respond with "ขอบคุณสำหรับข้อมูล เราจะนำไปปรับปรุงความแม่นยำครับ".
- **Step 5:** Now click the **"📊 เทียบข้อมูล"** (Compare API) button.
- **Expected Result:** In the comparison summary, observe the `% ความแม่นยำ` (Accuracy Score). The API that triggered the alert (e.g., Tomorrow.io หรือ Xweather) จะมีคะแนนความแม่นยำลดลงจากการกด False Alarm ของคุณ 
- **Step 6 (Optional Database Check):** You can open `fonmayang.db` (using an SQLite viewer like DB Browser for SQLite) or look into your Firebase Console (if using Firestore) and check the `api_reliability` table/collection. You should see that `false_alarms` has incremented for that specific API endpoint, and the `accuracy_score` has been dynamically adjusted.
