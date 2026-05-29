# Manual Verification Guide

- Step 1: Start the application locally by navigating to the `backend` directory and running `uvicorn app.main:app --reload`.
- Step 2: Open another terminal and simulate a Telegram location message using `curl`:
  `curl -X POST http://localhost:8000/api/v1/webhook/telegram -H "Content-Type: application/json" -d '{"message": {"chat": {"id": 12345}, "location": {"latitude": 13.75, "longitude": 100.50}}}'`
- Expected Result: The server should return `{"status": "ok"}`. In the server logs, you will see a log indicating it's sending a forecast message with the inline keyboard ("คุณต้องการให้ระบบจดจำตำแหน่งนี้สำหรับการแจ้งเตือนอัตโนมัติไหม?").

- Step 3: Simulate the user clicking the "จำ 2 เดือน" (loc_2m) inline button by sending a `callback_query` payload:
  `curl -X POST http://localhost:8000/api/v1/webhook/telegram -H "Content-Type: application/json" -d '{"callback_query": {"id": "query_1", "from": {"id": 12345}, "message": {"message_id": 1, "chat": {"id": 12345}}, "data": "loc_2m_13.75_100.50"}}'`
- Expected Result: The server returns `{"status": "ok"}`. The location is saved into the SQLite database. The logs should show it sending an `answerCallbackQuery` and an `editMessageReplyMarkup` to remove the keyboard.

- Step 4: Simulate the user sending the `/mylocation` command:
  `curl -X POST http://localhost:8000/api/v1/webhook/telegram -H "Content-Type: application/json" -d '{"message": {"chat": {"id": 12345}, "text": "/mylocation"}}'`
- Expected Result: The server returns `{"status": "ok"}`. The logs should show it fetching the location and preparing a message with the coordinates, expiration date, and a "🗑️ ลบพิกัดเดิม" inline button.

- Step 5: Simulate the user clicking the "🗑️ ลบพิกัดเดิม" button to delete the location:
  `curl -X POST http://localhost:8000/api/v1/webhook/telegram -H "Content-Type: application/json" -d '{"callback_query": {"id": "query_2", "from": {"id": 12345}, "message": {"message_id": 2, "chat": {"id": 12345}}, "data": "loc_del"}}'`
- Expected Result: The server returns `{"status": "ok"}`. The location is removed from the database, and the server acknowledges the deletion via `answerCallbackQuery`.