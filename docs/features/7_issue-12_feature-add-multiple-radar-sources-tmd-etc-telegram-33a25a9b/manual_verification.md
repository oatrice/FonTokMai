### Manual Verification Guide

- **Step 1:** Start your local development server for the backend. (Do NOT use `python main.py` as it's configured for Firebase Functions). 
  - First, make sure port 8000 is free. If you got `Address already in use`, run: `lsof -ti:8000 | xargs kill -9`
  - Then, start the server with: `cd backend && uvicorn app.main:app --reload`
- **Step 2:** Ensure your local server is publicly accessible for Telegram webhooks (e.g., using `lt --port 8000` via localtunnel) and the webhook URL is registered with your bot.
- **Step 3:** Open the Telegram app and go to your bot's chat. Send a **Location Pin** to the bot so it has a saved coordinate for your user account.
- **Step 4:** Send the `/radar` command to the bot in the chat.
- **Expected Result 1:** The bot should respond with the text "📡 คุณสามารถเช็คเรดาร์ฝนด้วยตัวเองได้จากแหล่งข้อมูลเหล่านี้:" and display three inline keyboard buttons:
  - 📡 Zoom Earth (clicking opens zoom.earth at your saved coordinates)
  - 🌪️ Windy Radar (clicking opens windy.com at your saved coordinates)
  - 🇹🇭 TMD Radar (clicking opens weather.tmd.go.th)
- **Step 5:** In a separate terminal, trigger a simulated proactive rain alert by running the force test script: `python backend/force_test_alert.py`
- **Expected Result 2:** You should receive a proactive rain alert message on Telegram informing you about the rain ETA. At the bottom of this message, the exact same three inline keyboard buttons for radar sources should be visible and clickable.
