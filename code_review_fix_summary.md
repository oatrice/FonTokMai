# Code Review & Bug Fixes Summary

## 1. Resolved Test Failures (11 Tests Fixed)
- **`backend/tests/test_manual_targeting.py` (7 tests PASS)**:
  - **Issue:** Model `UserLocation` was missing the `locked_target_cx` and `locked_target_cy` columns in `models.py`. In addition, `webhook_callbacks.py` had an inner `import process_telegram_location` causing an `UnboundLocalError`.
  - **Fix:** Restored `locked_target_cx` and `locked_target_cy` to `UserLocation`. Removed duplicate local import. All 17 manual targeting tests now pass.
- **`backend/tests/test_db.py` (1 test PASS)**:
  - **Issue:** `inspect(conn)` was called directly on an `AsyncConnection` object, which SQLAlchemy 2.0 does not support.
  - **Fix:** Switched to `conn.run_sync(get_cols, table_name)`. All 6 DB migration and schema tests now pass.
- **`backend/tests/test_scheduler.py` (3 tests PASS)**:
  - **Issue:** Tests failed because the presence verification intercept was triggering for newly introduced presence defaults (`always_ask`), altering notification messages and call counts.
  - **Fix:** Configured `presence_policy="always_notify"` on test locations where direct rain alerts are tested, and updated the `get_repo_context` call count assertion from 3 to 4 (accounting for the new `AlertNotificationLog` record). All 17 scheduler tests now pass.

## 2. Frontend React Performance & Linter Fixes
- **`GCPCostBreakdown.tsx`**:
  - Eliminated synchronous `setState` inside `useEffect` (cascading renders) by migrating data fetching to `useSWR`.
  - Connected the refresh button to `mutate()` and cleaned up component skeleton loaders.
- **`RunwayCounter.tsx`**:
  - Eliminated synchronous `setState` inside `useEffect` by using `useSyncExternalStore` for client-side mounting and `localStorage` synchronization.
- **`DonationModal.tsx` & `TokenRecoveryModal.tsx`**:
  - Removed explicit `any` types in catch blocks, replacing with type-safe `unknown` and `instanceof Error`.
- **`admin/locations/page.tsx` & `admin/metrics/page.tsx`**:
  - Cleaned up unused imports and unused state variables.

## 3. Security Check
- Checked `/mock_rain` command: Verified that `@cmd_router.bind("/mock_rain", requires_admin=True)` is enforced so non-admin users cannot call it.
