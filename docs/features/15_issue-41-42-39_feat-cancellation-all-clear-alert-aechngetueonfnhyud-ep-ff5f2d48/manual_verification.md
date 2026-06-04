# Manual Verification Guide

### 1. Verification for All-Clear Alert
- **Step 1:** Add a mock state to simulate rain by sending the `/devmock rain` command in the developer Telegram chat. Wait for the scheduler to trigger a rain alert.
- **Step 2:** Ensure you receive the rain alert message. This successfully stores your `last_alert_max_rain` > 0.
- **Step 3:** Change the mock state to simulate clear weather by sending the `/devmock clear` command.
- **Step 4:** Wait for the next scheduler execution (cron job).
- **Expected Result:** You should receive a Telegram message stating "☀️ สภาพอากาศ ณ พิกัด... เคลียร์แล้ว (ไม่มีแนวโน้มฝนตกในขณะนี้)" and the system should successfully reset your `last_alert_max_rain` to 0.0.

### 2. Verification for Interactive Ground Truth Feedback
- **Step 1:** Trigger a rain alert either by using `/devmock rain` or waiting for an actual rain alert.
- **Step 2:** Locate the new button "❌ แจ้งเตือนผิดพลาด (ฝนไม่ตกจริง)" attached to the rain alert message.
- **Step 3:** Click the button.
- **Expected Result:** You should see a Telegram popup (toast notification) saying "ขอบคุณสำหรับข้อมูล เราจะนำไปปรับปรุงความแม่นยำครับ". Verify that the SQLite `user_feedbacks` table or the Firestore `user_feedbacks` collection has a new entry with `feedback_type = 'false_alarm'`.

### 3. Verification for Insights API Comparison
- **Step 1:** Locate the new button "📊 เทียบข้อมูล 3 API" attached to a recent rain alert message.
- **Step 2:** Click the button.
- **Expected Result:** You should immediately see a toast notification saying "กำลังดึงข้อมูลเปรียบเทียบ..." followed by the original alert message being edited to display the API comparison breakdown (showing data for Tomorrow.io, Rainbow Local, and Rainbow Global side by side).
