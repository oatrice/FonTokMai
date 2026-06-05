# Task Checklist: Batch H - Disasters & Natural Hazards Alerts

## 1. Database & Models
- `[x]` Add `DisasterAlertHistory` model to `backend/app/models.py`.
- `[x]` Update database schema (Alembic/SQLite create tables).

## 2. API Integration & Services
- `[x]` **Earthquake Service (`earthquake.py`)**:
  - `[x]` Implement `fetch_usgs_geojson()` for polling.
  - `[x]` Implement `start_emsc_websocket()` for push notifications.
- `[x]` **Xweather Service (`xweather.py`)**:
  - `[x]` Implement `get_active_tropical_cyclones()`.
  - `[x]` Implement `get_active_fires()`.

## 3. Core Logic & Spatial Matching
- `[x]` Create a utility function for Haversine distance calculation.
- `[x]` Implement logic to filter users within impact radius.
- `[x]` Implement logic to check/prevent duplicate alerts using `DisasterAlertHistory`.

## 4. Telegram Messaging
- `[x]` Add alert templates for Earthquakes in `telegram.py`.
- `[x]` Add alert templates for Cyclones in `telegram.py`.
- `[x]` Add alert templates for Fires in `telegram.py`.

## 5. Scheduler & Background Tasks
- `[x]` Add `check_disasters_routine` to `scheduler_tasks.py` (polling USGS, Cyclones, Fires).
- `[x]` Hook up `start_emsc_websocket` in `main.py` startup events.

## 6. Testing & Verification
- `[x]` Add/run unit tests for spatial matching.
- `[x]` Run manual mock tests.
