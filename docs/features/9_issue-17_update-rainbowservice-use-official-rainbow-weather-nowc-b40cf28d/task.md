# Issue #17: Update RainbowService to use official Rainbow Weather API

- [x] Update tests to mock the new API response structure (Red)
- [x] Update `RainbowService.API_URL` and endpoint parameters
- [x] Implement new parsing logic for `forecast` and `precipRate`
- [x] Refactor code and verify all tests pass (Green/Refactor)
- [x] อัปเดตไฟล์ `backend/app/services/rainbow.py` ให้รองรับพารามิเตอร์ `endpoint_type`
- [x] เพิ่มฟังก์ชัน `edit_telegram_message` ในไฟล์ `backend/app/services/telegram.py`
- [x] อัปเดต `process_telegram_location` ใน `backend/app/routers/webhook.py` เพื่อรองรับการสลับแหล่งข้อมูลผ่าน Inline Keyboard
- [x] อัปเดต `handle_callback_query` ใน `webhook.py` เพื่อดักจับปุ่มสลับ Endpoint
- [x] ปรับปรุง Unit Tests ใน `backend/tests/test_services.py` 
- [x] Notify task complete
