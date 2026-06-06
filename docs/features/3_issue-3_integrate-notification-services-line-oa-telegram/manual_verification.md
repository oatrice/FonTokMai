# Manual Verification Guide: Telegram Webhook

Follow these steps to manually test the Telegram Webhook integration locally:

- **Step 1:** Start the FastAPI application locally.
  Run the following command from the `backend` directory (ensure your virtual environment is activated):
  ```bash
  uvicorn app.main:app --reload
  ```
  *Ensure the server starts without errors and is listening on `http://127.0.0.1:8001`.*

- **Step 2:** Simulate a Telegram Location Message via `curl`.
  Open a new terminal window and execute the following `curl` command to send a mocked Telegram payload containing a location:
  ```bash
  curl -X POST "http://127.0.0.1:8001/api/v1/webhook/telegram" \
       -H "Content-Type: application/json" \
       -d '{
         "update_id": 123456789,
         "message": {
           "message_id": 1,
           "chat": {"id": 12345678},
           "location": {
             "latitude": 17.1664,
             "longitude": 104.1486
           }
         }
       }'
  ```

- **Step 3:** Check the Immediate API Response.
  - **Expected Result:** The API should respond immediately with `{"status":"ok"}`. This confirms the webhook received the location and handed it off to the background task successfully.

- **Step 4:** Check the Backend Server Logs.
  Return to the terminal where `uvicorn` is running and observe the logs.
  - **Expected Result:** Since `TELEGRAM_BOT_TOKEN` defaults to `mock_token`, the server will attempt to contact the Telegram API with an invalid token. You should see an error log or an HTTP exception from `httpx` indicating it couldn't send the message (e.g., 404/401 from Telegram). This proves the background task ran and executed the Rain prediction logic successfully before attempting to send the message.

- **Step 5 (Optional):** Simulate an Irrelevant Telegram Message.
  Run the following `curl` to simulate a message without location data:
  ```bash
  curl -X POST "http://127.0.0.1:8001/api/v1/webhook/telegram" \
       -H "Content-Type: application/json" \
       -d '{
         "update_id": 123456789,
         "message": {
           "message_id": 2,
           "chat": {"id": 12345678},
           "text": "Hello bot"
         }
       }'
  ```
  - **Expected Result:** The API should respond with `{"status":"ignored"}`. No background task should be triggered, and no errors should appear in the `uvicorn` logs.
