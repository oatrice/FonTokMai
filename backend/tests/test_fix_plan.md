# Test Fix Plan for MR !99

The comprehensive test suite run reported 13 failures across 4 test files. Here is the breakdown and fix plan:

## 1. `backend/tests/test_scheduler.py` (3 failures)
- **Failures:** `test_check_rain_and_alert_rain_incoming`, `test_check_rain_and_alert_smart_cooldown_override`, `test_check_rain_and_alert_with_advanced_alerts`.
- **Cause:** These tests mock the scheduler's check for rain. With the new Presence Check feature (MR !98), when rain is detected and an alert is ready to be sent, the system now intercepts the message and sends a "Presence Verification" prompt instead of the actual rain alert or advanced alert. The tests still assert the older behavior (looking for "อัปเดต" or counting 2 messages).
- **Fix:** Update the tests to either mock `is_presence_verified` to True, or change the assertions to expect the presence verification message (`ตอนนี้คุณอยู่ที่นี่...`).

## 2. `backend/tests/test_manual_targeting.py` (7 failures)
- **Failures:** Tests related to the `/lock` command and grid lock inline callbacks.
- **Cause:** The recent changes to location commands likely altered how locations are parsed, stored, or how the callback payloads are handled, breaking the manual targeting tests. Or the sensitive data filter changes caused an issue with mock arguments.
- **Fix:** Inspect the changes made in `backend/app/routers/webhook_commands.py` (specifically `handle_lock_command` and `handle_grid_lock_callback`) against the test setup in `test_manual_targeting.py`. Fix the mocked database setup or the assertions.

## 3. `backend/tests/test_firestore.py` (2 failures)
- **Failures:** `test_save_location_two_months`, `test_save_location_forever` (TypeError).
- **Cause:** The recent Location CRUD update (MR !97) added new fields like `snoozed_until`. The tests likely pass incorrect types or missing arguments to `save_location` or when instantiating `UserLocation`.
- **Fix:** Update the test data to match the new `UserLocation` schema.

## 4. `backend/tests/test_db.py` (1 failure)
- **Failures:** `test_schema_migrations_add_missing_columns_idempotently`.
- **Cause:** A new model/column was added (e.g., `AlertNotificationLog` or fields in `UserLocation`), and the migration test logic is asserting on an outdated schema state or failing to migrate the new column properly in SQLite.
- **Fix:** Update the expected columns list in the migration test.
