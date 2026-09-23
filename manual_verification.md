# Manual Verification: Architecture Refactor Phase 1

This MR focuses on extracting `DevSettings` (a global Pydantic model for untyped development config) and `AlertFormatter` (a decoupled formatter for Telegram alerts). It is foundational for subsequent MRs.

## Verification Steps

### 1. Verify Application Startup
Run the application to ensure it boots without dictionary-access errors from old `_DEV_CONFIG`.
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
**Expected:** The app starts successfully with no startup errors.

### 2. Verify Dev Mock Endpoints (DevSettings Mutation)
The `/api/webhook/devmock` endpoint mutates the new `DevSettings` object instead of the old dictionary.
```bash
curl -X POST "http://localhost:8000/api/webhook/devmock" -H "Content-Type: application/json" -d '{"command": "/devmock set search_radius 90", "chat_id": 123}'
```
**Expected:** Response should indicate that `search_radius` was set to `90`. The internal `DevSettings` object correctly applies this configuration.

### 3. Verify Weather Manager (DevSettings Reading)
Trigger a weather prediction to ensure `weather_manager.py` successfully reads from `DevSettings`.
```bash
curl -X POST "http://localhost:8000/api/webhook/telegram" -H "Content-Type: application/json" -d '{"message": {"text": "/rain", "chat": {"id": 123}}}'
```
**Expected:** The system processes the request normally, generating predictions without throwing `AttributeError` or `KeyError` related to `_DEV_CONFIG`.

### 4. Verify Alert Formatter
Wait for the background scheduled task to trigger `check_rain_and_alert`, which now uses `AlertFormatter`. Alternatively, check the unit tests for format parity.
```bash
pytest backend/tests/test_alert_formatter.py
```
**Expected:** The tests pass, proving that the generated Thai text matches the original legacy strings exactly.

## Scope Checked
- Foundational decoupling only.
- Test suites run green, meaning no regressions were introduced to the legacy God Module paths.
