## What does this MR do?
- Implements Phase 3 of the architecture refactor (`NowcastPort` & `TMDNowcastAdapter`).
- Extracted `_get_tmd_prediction` logic (~400 LOC) out of `WeatherManager` into `TMDNowcastAdapter`.
- Added a simple port interface `NowcastPort`.
- Maintains backward compatibility via `WeatherManager._get_tmd_prediction` acting as a facade for the adapter.

## Why are we doing this?
To decouple the massive domain logic (radar image processing and tracking) from the webhook service layer (`WeatherManager`), making the codebase easier to test, maintain, and swap components in the future.

## How to verify
1. All `pytest` tests pass.
2. E2E Radar logic should function normally without regressions.
