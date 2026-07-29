# FonMaYang 🌧️

**v0.66.0** — Real-Time Rain Prediction System for Isan (Northeastern) Region, Thailand  
Predicts rainfall 15–90+ minutes in advance using TMD Radar Images + Optical Flow Cloud Tracking.

---

## Features

- **TMD Radar Processing** — Downloads and processes TMD radar images (kkn120, kkn240, skn240) using Optical Flow.
- **Rain Prediction** — Forecasts rain arrival time (ETA) and intensity (dBZ) up to 90+ minutes in advance.
- **Real-Time Leaderboard & SSE Broadcaster** — Retro-arcade glassmorphic live leaderboard with server-sent events (`/api/v1/events/stream`) and 15s heartbeats (Issues #148, #157).
- **Dynamic Circuit Breaker & Resiliency** — Automatically downgrades external API failures to free fallbacks, supported by Emergency Overdrive (`INVINCIBLE` status).
- **Gamified Financial Transparency & Jars** — Real-time Runway Engine decay, Budget Jars, Milestone Progress Bar (`GET /api/milestones`), GCP Infrastructure Cost Breakdown (`GET /api/v1/metrics/gcp-costs`), and Donation Lock.
- **Zero-PII Payments & Auto Payouts** — Anonymous Auth, Account Recovery Keys, Zero-PII Stripe Webhook, and Stripe Auto Payout lifecycle handling (`payout.created`, `payout.paid`, `payout.failed`).
- **Manual Target Locking** — Select and lock specific rain cloud targets to track their precise direction and distance on radar images.
- **Multi-Provider Fallback** — Fallback support for Tomorrow.io, Rainbow API, Xweather, and Open-Meteo.
- **Telegram & LINE Bots** — Automated alerts with tracking radar images, timeline graphs, and multi-frame analysis.
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

## DevOps & QA Scripts

| Script | Description |
|---|---|
| `scripts/run_all_production_qa_tests.sh` | Run complete 6-suite Production QA & Full-Stack Playwright E2E test suite |
| `scripts/generate_qa_report.py` | Generate standalone HTML QA report with embedded authentic screenshots |
| `backend/scripts/check_public_access.sh` | Audit Cloud Run IAM public access |
| `backend/scripts/disable_public_access.sh` | Disable API public access and configure private mode |
| `backend/scripts/setup_iam_roles.sh` | Configure IAM roles for Cloud Run Service Account |
| `backend/scripts/setup_schedulers.sh` | Apply Cloud Scheduler jobs from config |
| `backend/scripts/sync_schedulers.py` | Sync scheduler config from GCP |
| `backend/scripts/migrate_issue145.py` | Migrate user location for Nong Khai House and deprecate stale home coordinates |

---

## Running Tests

### Backend Unit Tests
```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ -v
```

### Full-Stack Playwright E2E & Production QA Test Suite
```bash
./scripts/run_all_production_qa_tests.sh
```

Key test suites & files:
- `scripts/run_all_production_qa_tests.sh` — 6-Suite Full-Stack E2E test runner (Runway, Budget Jars, Circuit Breaker, Stripe, Webhooks, A11y)
- `tests/e2e/test_suite_1_runway_overdrive.py` — Live Runway Engine & Emergency Overdrive tests
- `tests/e2e/test_suite_2_budget_jars.py` — Budget Jars 50/30/20 & zero-balance safety tests
- `tests/e2e/test_suite_3_circuit_breaker.py` — Circuit Breaker active danger badge tests
- `tests/e2e/test_suite_4_stripe_auto_refresh.py` — Stripe webhook auto-balance update tests (5,140 → 7,640 THB)
- `tests/e2e/test_suite_5_serverless_webhooks.py` — Serverless Telegram webhook fast response contract (< 200ms)
- `tests/e2e/test_suite_6_theme_a11y.py` — Dark Glassmorphic Theme & Keyboard Accessibility tests
- `tests/e2e/test_navigation.py` — Breadcrumbs navigation hierarchy tests

---

## Version History

See [CHANGELOG.md](CHANGELOG.md) for full history.

Current: **v0.63.0** — Dynamic Next.js API Rewrites for Vercel Deployment to Cloud Run Backend (`BACKEND_URL`) & FastAPI CORS Middleware configuration.
