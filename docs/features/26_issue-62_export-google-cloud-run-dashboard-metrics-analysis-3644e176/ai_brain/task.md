# Task List: Batch F (Xweather Integration & Advanced Alerts)

- `[x]` **Setup & Configuration**
  - `[x]` Add Xweather env variables to `.env.example` and config loaders (`XWEATHER_CLIENT_ID`, `XWEATHER_CLIENT_SECRET`, `XWEATHER_ENABLED`).
- `[x]` **Issue #32: Xweather Service & Minutecast (TDD)**
  - `[x]` Write failing tests for `XweatherService.predict_rain_by_location` and Circuit Breaker logic.
  - `[x]` Implement `XweatherService` to pass tests (fetch minutecast, handle 429/403 with Circuit Breaker).
  - `[x]` Write failing tests for `WeatherManager` fallback chain (Xweather -> Tomorrow.io -> Rainbow).
  - `[x]` Update `WeatherManager` to include Xweather as primary and pass tests.
- `[x]` **Issue #33-35: Advanced Alerts (TDD)**
  - `[x]` Write failing tests for `get_advanced_alerts` (Advisories, Lightning, Stormcells).
  - `[x]` Implement `get_advanced_alerts` in `XweatherService` and expose via `WeatherManager`.
  - `[x]` Write failing tests for secondary Telegram message box in `scheduler_tasks.py`.
  - `[x]` Implement secondary Telegram message box logic.
  - `[x]` Update `scheduler_tasks.py` to fetch advanced alerts and trigger separate Telegram messages.
- `[ ]` **End-to-End Verification**
  - `[ ]` Run all tests.
  - `[ ]` Test via `force_test_alert.py`.
