# FonMaYang 🌧️

**v0.58.0** — Real-Time Rain Prediction System for Isan (Northeastern) Region, Thailand  
Predicts rainfall 15–90+ minutes in advance using TMD Radar Images + Optical Flow Cloud Tracking.

---

## Features

- **TMD Radar Processing** — Downloads and processes TMD radar images (kkn120, kkn240, skn240) using Optical Flow.
- **Rain Prediction** — Forecasts rain arrival time (ETA) and intensity (dBZ) up to 90+ minutes in advance.
- **Manual Target Locking** — Select and lock specific rain cloud targets to track their precise direction and distance on radar images.
- **Multi-Provider Fallback** — Fallback support for Tomorrow.io, Rainbow API, Xweather, and Open-Meteo.
- **Telegram Bot** — Automated alerts via Telegram with tracking radar images, timeline graphs, and multi-frame analysis.
- **LINE Bot** — Alerts and location/command processing via LINE Official Account with latest radar images and cloud analysis charts.
- **Multi-Frame Radar Analysis** — Multi-frame strip images (up to 6 frames) ordered chronologically with trajectory overlays and per-frame growth/decay %.
- **Scheduler** — Cloud Scheduler triggers automated polling and alerts every 15 minutes.

---

## Bot Commands (Telegram & LINE)

---

### User Commands
| Command | Description |
|---|---|
| (Send Location) | Forecast rain at the sent location and save it for proactive notifications |
| `/rain` | View weather for the most recent location |
| `/rain tmd-radar` | Force use of TMD Radar endpoint |
| `/rain <location_name>` | View weather for a saved location |
| `/radar` | View latest static radar image for the most recent location |
| `/tracking` | View tracking radar image with storm vectors for the most recent location |
| `/timeline` | View rain duration timeline graph for the most recent location |
| `/nowcast` | View animated nowcast GIF for the most recent location |
| `/lock <grid>` | Lock a rain cloud target by grid square (e.g. `/lock C4`) or manual position |
| `/unlock` | Unlock the currently tracked rain cloud target |

### Developer Commands (DEVELOPER_CHAT_IDS only)
| Command | Description |
|---|---|
| `/bypass <password>` | Verify password to activate Emergency Admin Bypass (1 hour) |
| `/bypass_logout` | Log out from Emergency Admin Bypass |
| `/metrics [days]` | Export Cron metrics history as a CSV file |
| `/setbudget <amount>` | Dynamically adjust GCP budget limit |
| `/job <pause/resume> <job_name>` | Pause or resume specific Cloud Scheduler Jobs |
| `/status` | Check backend system status, remaining budget, and Cloud Scheduler Jobs |
| `/restore_public_access` | Restore Public Access permission for Cloud Run API |
| `/disable_public_access` | Revoke Public Access permission for Cloud Run API (Private mode) |
| `/devmock help` | Show all devmock commands |
| `/devmock rain` | Simulate heavy rain (Boost real clouds) |
| `/devmock storm` | Simulate storm (Create 5 mock clouds) |
| `/devmock clear` | Simulate clear sky |
| `/devmock error` | Simulate all APIs failing |
| `/devmock off` | Turn off mock mode |
| `/devmock config` | View and adjust analysis settings (including decay_enabled and prediction_steps) |
| `/devmock scenario <params>` | **Simulate parametric rain scenarios** (see below) |

#### `/devmock scenario` Parameters
```
rain_in:N        Rain will arrive in N minutes
rain_stopping:N  Rain will stop in N minutes
no_rain          No rain (Test wind only)
dbz:N            Rain intensity dBZ (15–75, default 35)
wind:N           Wind speed km/h (default 20)
wind_dir:X       Wind direction: N/NE/E/SE/S/SW/W/NW (16 points)
growth:N         Growth rate ±0.0–1.0
clusters:N       Number of cloud clusters 1–5 (default 1)
```

**Examples:**
```
/devmock scenario rain_in:20 dbz:40 wind:60 wind_dir:N
/devmock scenario rain_stopping:10 dbz:30
/devmock scenario no_rain wind:45 wind_dir:SE
/devmock scenario rain_in:5 dbz:55 growth:0.3 clusters:3
```

---

## Architecture

```
Telegram / LINE Webhook
    │
    │
    ▼
WeatherManager.predict_rain()
    ├── TMDRadarProcessor  ← Optical Flow + Cloud Tracking + Target Lock
    ├── TomorrowService    ← Fallback 1
    ├── XweatherService    ← Fallback 2 (disabled by default)
    ├── RainbowService     ← Fallback 3
    └── OpenMeteoService   ← Fallback 4 (wind data)
```

**Key Services:**
- `backend/app/services/weather_manager.py` — Orchestrator, mock state handler, manual target tracking
- `backend/app/services/billing_service.py` — GCP/AWS Billing and cost aggregation pipeline
- `backend/app/services/tmd_radar/clustering.py` — OpenCV contours, rain cluster detection, circular masking
- `backend/app/services/tmd_radar/tracking.py` — Optical flow wind vectors, cloud tracking, trajectory predictions
- `backend/app/services/tmd_radar/processor.py` — Main orchestrator for TMD Radar processing
- `backend/app/services/notification.py` — Abstract notification dispatcher (Telegram & LINE)
- `backend/app/routers/webhook.py` — Telegram webhook entry point
- `backend/app/routers/line_webhook.py` — LINE webhook entry point
- `backend/app/scheduler_tasks.py` — Scheduled rain alerts

---

## DevOps Scripts

| Script | Description |
|---|---|
| `backend/scripts/check_public_access.sh` | Audit Cloud Run IAM public access |
| `backend/scripts/disable_public_access.sh` | Disable API public access and configure private mode |
| `backend/scripts/setup_iam_roles.sh` | Configure IAM roles for Cloud Run Service Account |
| `backend/scripts/setup_schedulers.sh` | Apply Cloud Scheduler jobs from config |
| `backend/scripts/sync_schedulers.py` | Sync scheduler config from GCP |
| `backend/scripts/migrate_issue145.py` | Migrate user location for Nong Khai House and deprecate stale home coordinates |

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ -v
```

Key test files:
- `tests/test_billing_service.py` — GCP and AWS cost aggregation and billing tests
- `tests/test_tmd_radar_e2e.py` — End-to-end TMD radar processing
- `tests/test_e2e_mock_scenario.py` — Parametric mock scenario (33 tests)
- `tests/test_multiframe_analysis.py` — Multi-frame visualization (16 tests)
- `tests/test_line_integration.py` — LINE integration, commands, and webhook handling
- `tests/test_grpc_fork_config.py` — gRPC fork configuration and lazy tasks client tests
- `tests/test_async_enqueue_task.py` — Async tasks enqueue verification tests
- `tests/test_decay_logic.py` — Cloud decay toggle and prediction steps verification tests
- `tests/test_manual_targeting.py` — Manual target tracking, override logic, and visual indicators tests
- `tests/test_tracking_nowcast_commands.py` — Telegram `/tracking` and `/nowcast` command router & dispatch execution tests

---

## Version History

See [CHANGELOG.md](CHANGELOG.md) for full history.

Current: **v0.58.0** — Added GCP/AWS infrastructure cost aggregator (`BillingService`) and financial transparency system architecture docs (ADR 010).
