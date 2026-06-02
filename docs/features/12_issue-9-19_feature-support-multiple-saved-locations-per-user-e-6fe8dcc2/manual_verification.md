## Manual Verification Guide

Follow these steps to manually verify the multiple saved locations feature locally:

- Step 1: Start your local FastAPI backend server (e.g., `uvicorn app.main:app --reload`).
- Step 2: Set up a tunneling service like Ngrok (`ngrok http 8000`) and configure your Telegram bot webhook to point to the Ngrok URL (`/api/v1/telegram/webhook`).
- Step 3: Open Telegram and navigate to your FonMaYang bot chat. Send your current location using the attachment menu (paperclip icon -> Location).
- Expected Result: The bot should reply with inline buttons asking what to save the location as (e.g., `🏠 บ้าน (2 ด.)`, `💼 ที่ทำงาน (ตป.)`, `📍 ทั่วไป (2 ด.)`).

- Step 4: Click the `🏠 บ้าน (2 ด.)` button.
- Expected Result: The bot should edit the message or send a new message saying `บันทึกข้อมูลพิกัด home เรียบร้อยแล้ว`.

- Step 5: Send a **different** location to the bot.
- Expected Result: The bot should reply with the inline keyboard again, with the text `(คุณมีพิกัดเดิมบันทึกไว้อยู่แล้ว ต้องการบันทึกพิกัดนี้เป็นอะไร หรือลบของเดิมทิ้ง?)`.

- Step 6: Click the `💼 ที่ทำงาน (ตป.)` button.
- Expected Result: The bot should reply with `บันทึกข้อมูลพิกัด work เรียบร้อยแล้ว`.

- Step 7: Send the `/mylocation` command in the chat.
- Expected Result: The bot should display a list showing **both** locations (🏠 Home and 💼 Work) with their coordinates, expiration dates, and a `🗑️ ลบ` button for each specific location.

- Step 8: Click the `🗑️ ลบ Home` button.
- Expected Result: The bot should reply with `ลบข้อมูลพิกัด home เรียบร้อยแล้ว`.

- Step 9: Send the `/mylocation` command again.
- Expected Result: The list should now only display the 💼 Work location. The 🏠 Home location should be gone.

- Step 10: Trigger the manual rain check scheduler by sending a POST request to your backend:
  `curl -X POST http://localhost:8000/api/v1/cron/check-rain -H "X-Cron-Secret: <YOUR_SECRET>"`
- Expected Result: If it is going to rain at your saved 'Work' location within 60 minutes, you should receive a Telegram message that explicitly mentions the location name: `🌧️ ฝนกำลังเคลื่อนมาทางพิกัด 'Work' ของคุณ จะเริ่มตกในอีก ... นาที`. (If it is not raining, check the backend logs to ensure it queried the `get_active_locations` successfully).
