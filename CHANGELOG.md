# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.63.0] - 2026-07-23

### Added
- Added dynamic Next.js API rewrite configuration (`frontend/next.config.ts`) using `process.env.BACKEND_URL` environment variable for seamless Vercel production deployment to Cloud Run (Issue #207).
- Added `CORSMiddleware` configuration to FastAPI backend (`backend/app/main.py`) allowing Vercel deployment origins (`https://*.vercel.app`) and custom origin overrides via `ALLOWED_ORIGIN`.

## [0.62.0] - 2026-07-23

### Added
- Added Complete 6-Suite Production QA & Full-Stack E2E Playwright Test Runner (`scripts/run_all_production_qa_tests.sh`) covering Live Runway, Budget Jars, Circuit Breaker, Stripe Auto-Update, Telegram Webhook, and Dark Glassmorphism Accessibility (Issues #182, #191-#197, #201-#203).
- Added Automated Professional HTML QA Report Generator (`scripts/generate_qa_report.py`).

### Fixed
- Fixed Stripe Webhook zero-PII transaction balance update (`stripe_webhook.py`) by switching to absolute DB path resolution and robust `StripeObject` dict-style key access.
- Fixed UX Navigation in Dashboard Header (`Header.tsx` & `GlassNavbar.tsx`), introducing Breadcrumb hierarchy (`FonMaYang` › `System Dashboard`) and bidirectional navigation links between root (`/`) and dashboard (`/dashboard`).
- Fixed Test Suite 6 assertions to validate actual Dark Glassmorphism background color and keyboard `Tab` navigation.

## [0.61.0] - 2026-07-23

### Added
- Added Milestone Progress Bar & Donation Lock Endpoint (`GET /api/milestones`) (Issue #198).
- Added `SystemConfig` key `milestone_lock` to dynamically toggle donation lock state and anonymized recent donor lists.
- Added test suite `test_milestone_lock.py` for verifying milestone locked and unlocked states.

## [0.60.0] - 2026-07-23

### Added
- Added `CircuitBreaker` service (`backend/app/services/circuit_breaker.py`) supporting sync/async fallback execution for external APIs (Issue #196).
- Added Emergency Overdrive Mode (`INVINCIBLE` status) to `RunwayEngine` and SSE stream endpoint (`/api/v1/runway/stream?emergency_overdrive=true`) (Issue #197).
- Added test suite `test_circuit_breaker.py` for verifying failure thresholds and recovery.

## [0.59.0] - 2026-07-22

### Added
- Added Anonymous Authentication (`POST /api/v1/auth/anonymous`) and Account Recovery Key System (Issue #193, #194).
- Added Runway Engine (`backend/app/services/runway_engine.py`) and Budget Jars (`backend/app/services/budget_jars.py`) for real-time runway decay and jar allocation tracking (Issue #191, #195).
- Added Zero-PII Stripe Webhook Listener (`backend/app/routers/stripe_webhook.py`) with transaction hashing and event signature validation (Issue #192).
- Added test suites for Auth Recovery (`test_auth_recovery.py`), Budget Jars (`test_budget_jars.py`), Runway Engine (`test_runway_engine.py`), and Stripe Webhook (`test_stripe_webhook.py`).

## [0.58.0] - 2026-07-22

### Added
- Added infrastructure cost aggregation pipeline for GCP Cloud Billing and AWS Cost Explorer (`BillingService.aggregate_costs`), categorizing Baseline and Variable Costs (Issue #190).
- Added unit test suite for verifying cost aggregation logic (`tests/test_billing_service.py`).
- Added Gamified Financial Transparency System architecture documentation (ADR 010), including Web App Site Map and End-to-End Workflow Diagrams (`docs/architecture_decisions/010_gamified_finance_issue_batching_strategy.md` and `docs/web_app_architecture_and_sitemap.md`).

## [0.57.0] - 2026-07-21

### Added
- Added `/tracking` and `/nowcast` commands to Telegram Bot command set, allowing users to request rain tracking graphics and nowcast GIFs directly.
- Added GitLab Issue Generation Skill and Workflow Rules under `.agents/` directory.

### Changed
- Improved bandwidth efficiency by restricting auxiliary radar image uploads to Development environments.
- Added retry mechanism and exception handling for Telegram image rendering and dispatch for higher stability.

### Fixed
- Fixed rain cloud label allocation to restrict to A-Z with proximity fallback for future cloud labeling.
- Enhanced rain cluster locking display to pin correct positions even when centroid falls outside the crop window.

## [0.56.0] - 2026-07-21

### Added
- Added OpenCV Contour Processing and dBZ model-based radar clustering (Noise Filter) to replace Convex Hull logic.
- Added Chaikin corner-cutting smoothing and neon contour rendering for enhanced radar visualization.
- Added dynamic command menu setup for Telegram Bot environment modes.
- Added Admin/Developer Webhook Commands:
  - `/bypass` and `/bypass_logout` for temporary admin mode access/exit.
  - `/status` to audit backend health, public access status, and Cloud Scheduler Jobs.
  - `/metrics` to export cron execution logs as CSV files.
  - `/setbudget` to dynamically adjust system GCP budget limits.
  - `/job` to pause or resume individual Cloud Scheduler jobs.
  - `/restore_public_access` and `/disable_public_access` for Cloud Run API access control.

### Changed
- Improved cloud mask morphology processing using Gaussian Blur, HSV Thresholding, and geographic boundary color filtering.
- Refactored admin command authorization structure via `TelegramCommandRouter` dispatched through Cloud Tasks.

### Fixed
- Fixed overlapping ETA notification collisions by maintaining cloud label lock states.
- Enhanced stale data validation and backup frame loading mode during image missing events.

## [0.55.0] - 2026-07-14

### Added
- Added manual target tracking for rain cloud clusters on radar with grid-based coordinate mapping.
- Added target lock indicators, crosshairs, and line-of-sight path overlays pointing from cloud targets to current user location.
- Added webhook commands for locking and unlocking target rain clouds.
- Added test suite (`test_manual_targeting.py`) for manual target tracking verification.

### Changed
- Enhanced TMD Radar analysis view to prioritize user-selected tracked rain clouds.
- Updated `WeatherManager` to prioritize target-locked rain clouds saved in Firestore.

## [0.54.0] - 2026-07-13

### Added
- Added developer configuration options for cloud decay rate calculation (`decay_enabled`) and custom prediction steps (`prediction_steps`) in `_DEV_CONFIG`.
- Added test suite (`test_decay_logic.py`) to verify decay calculation mode.
- Added support for space-separated chatbot commands (e.g. `/devmock config prediction_steps: 13`).

### Changed
- Enhanced rain forecasting (`predict_rain`) to apply decay/growth rates to dBZ calculations when decay mode is enabled.
- Adjusted approaching cloud analysis (`find_approaching_clouds`) to compute `predicted_dbz` according to `decay_enabled`.
- Replaced fixed 7-step (90-min) prediction loop with configurable `prediction_steps` for flexible forecasting.

## [0.53.0] - 2026-07-13

### Added
- Added test suite (`test_tmd_polling_sync.py`) for radar polling & sync cache-busting verification.

### Changed
- Centralized TMD Radar Cache fetching/logging/verification in `TMDRadarProcessor.update_radar_cache`.
- Fixed stale cache checking in `WeatherManager` to fetch live TMD radar images immediately when cache is older than 20 minutes (Issue #167).
- Adjusted polling schedule in `schedulers.json` to 15-minute intervals (at :10, :25, :40, :55) to align with TMD publishing schedule (Issue #171).
- Added cache-busting query parameter (`?t=<timestamp>`) to prevent stale proxy/CDN responses.
- Cleared raw byte fields in `compare_all_apis` results to prevent `UnicodeDecodeError` during JSON serialization on `/compare`.

## [0.52.0] - 2026-07-13

### Added
- Added LINE OA chat commands: `/radar`, `/tracking`, `/timeline`, and `/nowcast`.
- Added guidance footer in proactive LINE alerts suggesting free quota image requests.
- Added `DEV_TELEGRAM_BOT_TOKEN` in `.env.example` and `deploy_cloudrun.sh`.

### Changed
- Refactored LINE OA command response to use **Reply API** (100% free quota) instead of Push API.
- Optimized proactive LINE alerts by omitting heavy radar images to conserve Push Message quota.
- Updated `LineNotificationService` to dynamically load credentials per request.
- Refactored budget alert webhook (`budget_webhook.py`) to be stateful (`budget_alert_80_sent` flag).

## [0.51.0] - 2026-07-08

### Added
- Added migration script `migrate_issue145.py` to register coordinates for `"Nong Khai House"` (`17.874829834, 102.740330372`) and clean up stale `"home"` coordinates.
- Added tests `test_async_enqueue_task.py` and `test_grpc_fork_config.py` to verify gRPC fork configurations and async tasks enqueuing.

### Changed
- Converted `CloudTasksService.enqueue_task` to be an asynchronous method (`async def`) utilizing `asyncio.to_thread` with a 5.0-second timeout to resolve Cloud Tasks 504 Deadline Exceeded timeouts.
- Implemented lazy client initialization in `CloudTasksService` to prevent gRPC connections from initiating before Uvicorn process forks, avoiding startup deadlocks.
- Enabled `GRPC_ENABLE_FORK_SUPPORT=1` in `app/main.py`, `.env.example`, and `deploy_cloudrun.sh` to ensure safe gRPC fork behaviors.
- Upgraded deprecated Cloud Firestore positional queries in `firestore.py` and unit tests to keyword-based `FieldFilter` query formats.
- Wrapped the Telegram webhook handler in `webhook.py` inside a top-level error handling block to provide user-facing alerts (`⚠️ ระบบยุ่งชั่วคราว กรุณาลองใหม่อีกครั้ง`) on failed task enqueues.

## [0.50.0] - 2026-07-08

### Added
- Added magic bytes validation (checking `GIF87a`/`GIF89a`) in `TMDRadarProcessor` to filter out invalid radar payloads and avoid OpenCV crashes.
- Created local verification script `verify_gif_validation.py` to test radar GIF validation.
- Documented LINE Rich Menu requirements and mock commands integration under `docs/requirement_analysis_line_rich_menu.md`.

### Changed
- Configured `/health` endpoint to support both `GET` and `HEAD` methods to resolve load balancer/Cloud Run checking issues (returning 405).
- Disabled Xweather by default (`XWEATHER_ENABLED=false`) in `.env.example` as the free trial has expired.

## [0.49.0] - 2026-07-07

### Added
- Integrated LINE Official Account (OA) notification services using `line-bot-sdk-python` v3.
- Created LINE Webhook router supporting location message sharing (for opting in to proactive rain alerts) and automatic weather forecasts.
- Implemented text command support on LINE OA (`/rain`, `/rain_pro`, `/check`, `/mylocation`, `/devmock`) to match existing Telegram bot command behaviors.
- Implemented local static media hosting (serving media via `WORKER_BASE_URL` / ngrok) during development to bypass cloud storage latency and permission constraints.

### Changed
- Refactored database and repository schemas (SQLite & Firestore) to convert `chat_id` columns from Integer/BigInteger to String, allowing compatibility with LINE's string-based user IDs.
- Updated existing test suites to handle string-based `chat_id` and updated developer command tests to patch environment settings during verification.

## [0.48.0] - 2026-07-07

### Added
- Added script `setup_iam_roles.sh` to configure GCP IAM roles for the Cloud Run runtime service account.
- Added environment synchronization checks under `backend/tests/test_deploy_env_sync.py`.

### Changed
- Refactored background scheduler to group locations per user (`chat_id`) and batch multiple alerts into a single consolidated notification.
- Optimized scheduler concurrency by reducing the semaphore threshold and introducing staggering delays (stagger) to prevent API rate limits (429 errors).
- Improved API comparison UI to map raw weather service exception traces to user-friendly, non-technical Thai error messages.
- Polished notification formatting spacing for locations with default names.

### Fixed
- Fixed alert duplicate spam for users with multiple active locations in the same proactive cycle.
- Fixed a mock scenario parsing bug where TMD radar prediction lists did not correctly inherit mock DBZ values.
- Cleaned up duplicate duration text rendering in Telegram webhook forecasts.

## [0.47.0] - 2026-07-07

### Added
- Added `/metrics` Telegram command for exporting system metrics logs as CSV.
- Added `/setbudget` Telegram command for dynamically adjusting the GCP Billing Budget.
- Added GCP Billing Budget Service using `google-cloud-billing-budgets` client library.
- Added `AdminBypass` model and repository methods (SQLite/Firestore) to support temporary authorization for restricted bot commands in Production.
- Added unit and integration tests for Admin Bypass and Developer commands.

### Changed
- Improved OCR timestamp extraction accuracy on cropped radar image headers using Tesseract PSM 6.
- Enhanced outdated static image detection to trigger automatic fallbacks to GIF loops.
- Updated radar configurations for Khon Kaen (`kkn240`) and Sakon Nakhon (`skn240`) to fetch high-resolution GIFs.

### Fixed
- Fixed GCP budget update display name mapping issues.
- Fixed weather prediction timing calculations and radar configuration crops.

## [0.46.0] - 2026-07-06

### Added
- Added support for generating weather timeline images with enhanced Thai font support and testing utilities.

### Changed
- Reorganized rain forecast message structure for better readability.
- Improved radar prediction pipeline by passing location names to enhance visualization labels.

## [0.45.0] - 2026-06-28

### Added
- Added support for managing Cloud Scheduler job states via configuration (`schedulers.json`) and deployment scripts.
- Added `hit_radius` parameter and approaching flags to storm detection for improved rain proximity alerts.
- Added label collision resolution logic for radar tracking images to prevent overlapping text.
- Added scripts for automated cross-commit output comparison and public access permission verification.

### Changed
- Refactored webhook endpoint logic to handle incoming event payloads securely and efficiently.
- Hidden radar trajectory ETA labels when overlapping with approaching rain clusters to improve readability.
- Refactored radar label positioning logic and connection line rendering thresholds.

### Fixed
- Fixed unhandled exceptions in webhook payload validation.
- Fixed checkout logic in `compare_commits.sh`.
- Fixed filtering of approaching clouds by status and ETA range to improve radar visualization accuracy.
- Fixed `is_loop` test logic and improved debug logging.

## [0.44.0] - 2026-06-26

### Added
- Added Parametric Mock Scenario System (`/devmock scenario`) for TMD Radar testing during dry spells. Developers can now simulate specific rain conditions via Telegram without waiting for actual rain events ([#121](https://gitlab.com/oatricedev/FonMaYang/-/issues/121)).
  - `rain_in:N` — simulate rain arriving in N minutes
  - `rain_stopping:N` — simulate rain stopping in N minutes
  - `no_rain` — simulate clear sky with wind-only data
  - `dbz:N` — set rain intensity (15–75 dBZ)
  - `wind:N wind_dir:X` — set wind speed (km/h) and direction (16 compass points)
  - `growth:N` — set cloud growth/decay rate
  - `clusters:N` — simulate 1–5 independent cloud clusters
- Added `/devmock help` command listing all available mock modes and scenario parameters.
- Added Multi-Frame Radar Analysis image (`radar_multiframe.png`) sent alongside existing radar images. Shows up to 6 consecutive radar frames side-by-side with per-frame cloud cluster trajectory overlays, colour-coded dBZ labels, and growth/decay percentage between frames.
- Added `generate_multiframe_analysis_image()` to `TMDRadarProcessor` for rendering the multi-frame strip visualization.
- Added `backend/scripts/check_public_access.sh` — a Cloud Run IAM audit script that checks whether `allUsers → roles/run.invoker` is bound on each service, with support for `--expect`, `--quiet`, and single-service modes.
- Added 49 new tests across `test_e2e_mock_scenario.py` (33 tests) and `test_multiframe_analysis.py` (16 tests).

## [0.43.0] - 2026-06-25

### Added
- Added Cloud Scheduler configuration management via `backend/config/schedulers.json` and scripts to apply or sync scheduler jobs from GCP.
- Added observability documentation covering uptime monitoring, queue metrics, Cloud Scheduler synchronization, and post-deployment performance checks.
- Added Cloud Tasks queue metrics endpoint tests.
- Added a Cloud Tasks historical dashboard analysis document for future queue depth tracking.

### Changed
- Updated EMSC worker processing to filter out low-magnitude and geographically irrelevant earthquake events before triggering webhook processing.
- Updated architecture decision records for incident recovery, radar polling, and issue batching strategies.

## [0.42.0] - 2026-06-24

### Added
- Implemented a multi-frame radar caching mechanism that automatically downloads and processes static radar images continuously.
- Added a smart automated GIF fallback recovery system. When static images are broken or unavailable, the system automatically falls back to downloading the full Loop GIF to prevent forecast outages, protected by a 30-minute cooldown.
- Added a low-confidence warning label (`⚠️ ข้อมูลขาดช่วง (ความแม่นยำต่ำ)`) to the rain summary in Telegram if the TMD radar data is older than 30 minutes.
- Added a new Telegram developer command (`/tmd_fallback [on|off]`) to dynamically toggle the GIF fallback logic on the fly.
- Implemented `system_settings` persistence across both Firestore and SQLite repositories for dynamic state management.

### Changed
- Improved optical flow normalization by accurately calculating time gaps between frames, standardizing all cloud movements to a 15-minute timeframe.
- Refactored radar fetching tasks to remove deprecated cache parameters and streamline the data processing pipeline.

## [0.41.0] - 2026-06-24

### Added
- Implemented outdated radar data detection (`is_outdated` flag) with automatic warning notifications sent to users via Telegram if the TMD Radar data is older than 45 minutes.
- Added IDC (+7 ICT) timestamp overlays to both zoomed tracking images and full-resolution radar images.

### Changed
- Increased the timestamp font size, padding, and layout margins on the full-resolution radar images to proportionally match the tracking image overlay.
- Updated Telegram Webhook responses to prioritize warning messages when data is outdated, hiding irrelevant ETA forecasts.
- Removed over 400 lines of duplicated code in the `TMDRadarProcessor` which was shadowing updated visual overlays.

### Fixed
- Fixed an issue where `send_telegram_photo` would sporadically fail with empty `ReadTimeout` exceptions due to the default 5-second `httpx` timeout. A 30-second timeout was added to ensure reliable delivery of image batches.

## [0.40.0] - 2026-06-23

### Added
- Added a cache warming mechanism to pre-populate the TMD radar cache directly from fresh loop GIFs.
- Added a fallback polling/fetching mechanism to weather manager to retrieve fresh radar frames when cache downloads fail or cache is empty/stale.
- Added diagnostic scripts and tools (`find_crop.py`, `visualize_radar.py`, `analyze_image.py`, OCR, and geolocation/coordinate testing) for auditing radar coordinate mapping and border detection.
- Added a new unit test run script (`backend/fix_tests.py`, `test.sh`, and test runner setups) and comprehensive E2E tests (`test_tmd_radar_e2e.py`) for TMD radar processing.
- Added an azimuthal projection mapping configuration for the Sakon Nakhon (skn240) radar station.

### Changed
- Improved `WeatherManager` and radar cache resilience by automatically caching freshly polled loop GIF frames back to Cloud Storage / Firestore to improve recovery from network and cache issues.
- Updated backend weather processing logic and enhanced TMD radar visualization overlay marker dimensions/pin markers.
- Refactored TMD radar frame fetching logic to simplify visual timeline rendering code.
- Cleaned up redundant prototype scripts to maintain project workspace hygiene.

### Fixed
- Fixed mapping issues with the `skn240` radar by using Azimuthal projection for improved coordinate accuracy.
- Fixed database initialization issues.

## [0.39.0] - 2026-06-22

### Added
- Added Cloud Run deployment config files (`cloudrun.env`, `deploy_cloudrun.sh`, `apply_cloudrun_config.sh`) to keep non-secret runtime settings versioned and reusable for CI/manual updates.
- Added an audit script (`audit_window_2026-06-21.sh`) for exporting Cloud Run logs and monitoring data for a specific incident window.

### Changed
- Refactored GitLab CI/CD to share Cloud Run auth handling, split config-only updates from source deploys, and keep deployment settings aligned with the versioned Cloud Run config.
- Extended the audit script with custom time-window flags, JSON export, output directory selection, and a generated `summary.json`.
- Reworked TMD radar pin mapping so cached static frames use static crop coordinates, fixing the production pin alignment shift.

### Fixed
- Fixed Cloud Run radar pin alignment on static frames by using the correct static coordinate mapping in `WeatherManager`.

## [0.38.0] - 2026-06-20

### Added
- Added a monitoring script (`setup_cloudrun_alerts.sh`) to automate the deployment of GCP Cloud Run alert policies for memory, latency, error rates, and instance counts.
- Added AI assistant configuration rules for Cursor and Aider to improve development workflows.

### Changed
- Updated GitLab CI configuration to disable CPU throttling (`--no-cpu-throttling`) for Cloud Run deployments to resolve severe CPU cold start latency issues during background tasks.
- Removed redundant and misleading memory garbage collection calls in the `WeatherManager` radar processing pipeline for improved code hygiene.

## [0.37.0] - 2026-06-20

### Added
- Added a dedicated test suite (`test_budget_webhook.py`) to verify the budget alert webhook handling for new alerts, duplicate (already private) alerts, and API error scenarios.

### Changed
- Refactored `_revoke_public_access` in the budget webhook router to return descriptive string status codes (`"REVOKED"`, `"ALREADY_PRIVATE"`, or `"ERROR"`) instead of booleans to prevent duplicate Telegram notifications on consecutive budget alerts.
- Updated GitLab CI configuration to adjust Cloud Run deployment options (`--timeout 300` and `--service-min-instances 1`), and cleaned up branch trigger rules to exclude CI/CD triggers on `.gitlab-ci.yml` changes for main branch backend and emsc_worker builds.

## [0.36.0] - 2026-06-20

### Added
- Added concurrency test scripts (`test_concurrency.py`, `test_concurrency_real.py`) and a mock test suite (`test_tmd_concurrency.py`) to verify the TMD radar cache locking mechanism under high concurrency.
- Added a module-level global lock and cache in `WeatherManager` to prevent concurrency stampedes when multiple requests query the same radar station simultaneously.

### Changed
- Refactored `WeatherManager` to replace the instance-level cache with a module-level global cache (`_GLOBAL_TMD_CACHE` and `_GLOBAL_TMD_LOCKS`) for shared cache state across class instances.
- Updated `test_tmd_radar_e2e.py` to assert against `_GLOBAL_TMD_CACHE` instead of `tmd_frames_cache`.

## [0.35.0] - 2026-06-19

### Added
- Added comprehensive end-to-end (E2E) test suite for the EMSC earthquake webhook (`test_e2e_earthquake.py`), including impact radius tests, alert triggering, and duplication checks.
- Added E2E test suite for the OCR service fallback chain (`test_e2e_ocr.py`) to verify behavior under normal parsing, garbage text inputs, and cache hit scenarios.
- Added E2E test suite for the weather manager fallback logic (`test_e2e_weather_manager.py`).
- Added E2E test suite for the Telegram worker command processing (`test_e2e_worker_rain.py`) and TMD radar pipeline (`test_tmd_radar_e2e.py`).

### Changed
- Refactored `render_hq_png` in `weather_manager.py` to a synchronous function to avoid unawaited coroutine warnings and prevent blocking the main asyncio event loop.
- Optimized weather manager response payload by disabling heavy radar GIF generation by default (setting `radar_gif_bytes` and `radar_hq_gif_bytes` to `None`).
- Updated GitHub Actions (`main.yml`) and GitLab CI (`.gitlab-ci.yml`) configurations to implement path-based conditional filters for deployments.

### Fixed
- Fixed integration and webhook tests by correcting the mock patch target of Telegram client requests to `app.services.telegram.httpx.AsyncClient.post` and adding an autouse mock for `CloudTasksService` to prevent real GCP Cloud Tasks creation.

## [0.34.0] - 2026-06-19

### Fixed
- Fixed `NameError: name 'os' is not defined` in `weather_manager.py` that caused TMD radar (`kkn240`) to silently crash, triggering unnecessary fallbacks to other weather providers.
- Corrected the Sakon Nakhon radar (`skn240`) bounding box (`SKN_BBOX`) from an incorrect 120km radius to the correct 240km coverage area, resolving "Location out of bounds" errors for users in Nong Khai and surrounding provinces.

### Changed
- Recalibrated `skn240` radar image crop coordinates (`static_crop_*` and `loop_crop_*`) using Hough Circle Detection on the live radar image for more accurate pixel-to-coordinate mapping.
- Injected `CRON_SECRET` into the Cloud Scheduler job environment in the GitHub Actions CI/CD workflow.

### Tests
- Added `test_tmd_radar_bounds_nong_khai` to verify that Nong Khai coordinates are correctly covered by `kkn240` and `skn240`, and out of bounds for `kkn120`.

## [0.33.0] - 2026-06-19
### Added
- Migrated CI/CD pipeline from GitLab to GitHub Actions, including a migration utility script.
- Added comprehensive project documentation in `README.md` to replace old prompt boilerplates.
- Added worker authentication to secure the backend worker endpoints.

### Changed
- Optimized TMD radar pipeline by transitioning to a highly efficient `radar_latest_cache` model, discarding loop GIF fetching in favor of lightweight T/T-1 static image comparisons.
- Refactored and modularized rain alert processing with an asyncio semaphore for robust concurrent execution.

## [0.32.0] - 2026-06-18
### Added
- Added a script to configure Cloud Logging exclusion filters to drop high-frequency HTTP 403 debug noise, optimizing log storage costs.
- Added a new AI skill (`api-endpoint-verification`) to prevent path hallucinations during automated agent operations.

### Changed
- Increased Cloud Run memory limit to 1GiB and optimized TMD radar frame processing to prevent Out Of Memory (OOM) errors.
- Enforced `--cpu-throttling` (Request-based billing) for Cloud Run deployment in GitLab CI to prevent unnecessary background CPU billing.
- Reduced the Artifact Registry keep limit to 2 images to ensure compliance with GCP free tier storage quotas.

### Fixed
- Fixed an issue with artifact version parsing to correctly identify and delete obsolete images during registry cleanup.

## [0.31.0] - 2026-06-18
### Added
- Created a standalone `emsc_worker` microservice to manage EMSC WebSocket connections, fully decoupled from the main FastAPI server to resolve scale-to-zero issues.
- Added a local mock WebSocket server (`mock_server.py`) inside `emsc_worker` to facilitate end-to-end local testing of earthquake alerts without waiting for live events.
- Added a new artifact registry cleanup script (`cleanup_artifact_registry.sh`) and integrated it into the GitLab CI/CD pipeline to manage storage costs (Issue #83).

### Changed
- Hardened Cloud Scheduler by setting `--max-retry-attempts=0` to prevent retry floods during backend failures.
- Reduced Cloud Run deployment timeout from 120s to 60s in the CI pipeline to fail-fast on startup errors.
- Refactored `emsc_worker` to natively load configuration via a `.env` file instead of relying on hardcoded systemd Environment directives for an improved local developer experience.

### Removed
- Removed the inline EMSC WebSocket startup routine from the main FastAPI server (`app.services.earthquake`) to achieve architectural decoupling.

## [0.30.0] - 2026-06-17
### Added
- Documented Incident Recovery and Stability Batching Strategy (ADR 008) to manage high-latency and memory leak issues.

### Changed
- **Hotfix:** Bypassed the expensive Cloud Vision and Gemini OCR fallback chain. The system now directly calls OCR.space with a 10-second fail-fast timeout to drastically reduce latency and Cloud Run costs.
- **Hotfix:** Temporarily disabled the EMSC WebSocket connection on startup to prevent memory leaks and scale-to-zero blockers.
- Updated GitLab CI/CD configuration to limit the maximum Cloud Run instances from 3 to 2 for improved cost control during high load.

## [0.29.0] - 2026-06-16
### Added
- Implemented a Budget Webhook auto-shutdown mechanism to automatically revoke Cloud Run public access when the billing budget limit is reached (Issue #72).
- Added setup scripts (`setup_budget_alert.sh` and `restore_public_access.sh`) for automating Google Cloud Budget alerts, Pub/Sub integrations, and service restoration.
- Implemented Cloud Tasks queue depth monitoring to track and alert on background worker metrics.
- Added Cloud Logging noise reduction filters (`setup_gcp.sh`) to exclude high-frequency debug logs and optimize billing costs (Issue #69).

### Changed
- Optimized TMD radar processing by implementing parallel station updates, significantly improving execution speed.

### Fixed
- Fixed the TMD radar loop URL resolution logic.

## [0.28.0] - 2026-06-16
### Added
- Created `setup_schedulers.sh` to automate the configuration and deployment of Google Cloud Scheduler jobs for all routine tasks.
- Integrated Cloud Scheduler setup script directly into the GitLab CI/CD pipeline for automated synchronization on every deployment.
- Added a dedicated runtime Service Account (`cloud-run-runtime`) with minimal IAM permissions (Principle of Least Privilege) for the Cloud Run service.

### Fixed
- Fixed a bug in the scheduler setup script where bash exit statuses were being overwritten by local variable declarations.

## [0.27.0] - 2026-06-16
### Added
- Implemented Google Cloud Tasks automation script (`setup_gcp.sh`) and optimized Cloud Run deployment settings (asia-southeast1, scale-to-zero, max instances).
- Added environment configuration and secret headers to securely authenticate background worker endpoints.
- Added comprehensive documentation and feasibility studies for Cloud Tasks integration, storage optimization, and future secret management.

### Changed
- Refactored radar processing to use asynchronous cloud storage fetching (`asyncio.to_thread`) to eliminate blocking I/O and prevent Cloud Run CPU throttling.
- Migrated long-running background tasks to Google Cloud Tasks for robust queue management and retry logic.
- Centralized module imports, implemented a 10-minute cache TTL for radar images, and modularized the developer mock disaster trigger logic.

### Fixed
- Fixed the Telegram webhook to gracefully ignore stale updates (older than 2 minutes) during reconnection, mitigating retry storms.

## [0.26.0] - 2026-06-08
### Added
- Implemented lightweight telemetry and an internal `MetricsService` with `/api/v1/metrics/export` endpoint to record and export cron routine runtime metrics.
- Added metrics recording for the `check_rain_and_alert` and `fetch_tmd_radar_routine` background tasks.
- Added a comprehensive guide (`gcp_logs_metrics_analysis_guide.md`) for analyzing GCP Cloud Run metrics and logs.

### Changed
- Refactored rain intensity reporting and ETA calculation for improved accuracy.

### Fixed
- Secured the metrics export endpoint to prevent unauthorized access and improved overall test coverage.

## [0.25.0] - 2026-06-08
### Added
- Implemented a unified caching system using Firebase Storage and Firestore for TMD radar images to prevent rate limiting and optimize processing speed.
- Added detailed info logging for cache hits during radar image fetches.

### Changed
- Improved rain cloud trajectory accuracy by implementing a perpendicular distance (Cross Track Error) check to ensure clouds are on a direct collision course.
- Enhanced rain cloud detection precision by refining noise filtering, clustering distances, and color calibration.
- Refactored and simplified cloud detection and trajectory cropping logic for better performance.

### Fixed
- Fixed false-positive rain detections by simplifying cloud detection and boundary cropping parameters.

## [0.24.0] - 2026-06-07
### Added
- Added the `/rain_pro` command to manually request advanced weather alerts (such as severe thunderstorms, lightning distance, and stormcell movement) alongside the standard rain forecast.
- Added `/devmock error` to test the API fallback and circuit breaker behavior manually.
- Implemented `SensitiveDataFilter` to mask API keys and secrets in logs for enhanced security.

### Changed
- Migrated OCR processing from the deprecated `google-generativeai` to the new `google-genai` SDK.
- Formatted `eta_minutes` to display in hours and minutes for better readability in alert messages.
- Refactored Webhook request processing to run inline instead of using `BackgroundTasks` to avoid Cloud Run CPU throttling.

### Fixed
- Fixed an issue where the storm direction was shown even when no rain was found.
- Resolved a `NameError` related to `answer_callback_query` in telegram webhooks.
- Fixed Open-Meteo API integration to correctly use the current wind speed/direction and corrected time filtering logic.
- Fixed Cloud Run Out-Of-Memory (OOM) crashes during TMD radar processing by increasing the memory limit to 1024Mi.
- Fixed FastAPI background tasks freezing on Cloud Run by adding the `--no-cpu-throttling` flag in CI deployment configuration.
- Fixed production UI issues on Linux environments by using Liberation fonts for radar images instead of tiny fallback fonts.
- Prevented empty exception strings from failing the weather API processing.

## [0.23.0] - 2026-06-07
### Added
- Implemented synthetic mock cloud injection for `/devmock storm` and `/devmock rain` to force tracking image generation and test alert workflows even during clear skies.
- Added animated multi-colored mock clouds that sweep across radar frames to verify Lagrangian tracking consistency.
- Added `/check` command alias for manual rain checks.

### Changed
- Separated `rain` and `storm` mock states to allow `/devmock rain` to test real cloud intensity boosting while `/devmock storm` overrides everything with a synthetic broad storm front.
- Synchronized the 5-color intensity bands (Green, Yellow, Orange, Red, Purple) across the timeline graph, tracking images, and the mock storm generator.

### Fixed
- Fixed an issue where the ETA timeline graph's X-axis labels would overlap and cascade off the canvas when multiple clouds arrived simultaneously.
- Fixed TMD radar noise rejection by ensuring synthetic mock clouds use exact TMD RGB color signatures.
- Fixed an indentation bug that caused mock clouds to be unintentionally boosted to 40 dBZ.
- Fixed OCR timezone logic to correctly interpret TMD radar timestamps as UTC, and added OCR cache invalidation.
- Fixed RGB to BGR color space conversions and channel swap issues that caused visual glitches and legend bleed-through in tracking images.
- Fixed tracking circle positioning by upgrading the cloud clustering algorithm to use Breadth-First Search (BFS).
- Fixed proactive rain notifications to properly include wind direction and attach tracking images.
- Fixed a bug where fake colored blobs were inappropriately visible during `/devmock rain`.

## [0.22.0] - 2026-06-06
### Added
- Implemented a resilient OCR fallback chain (Cloud Vision -> Gemini -> OCR.space) for robust TMD radar frame timestamp extraction.
- Added Firestore-based monthly quota management for Google Cloud Vision API to prevent exceeding free tier limits.
- Added radar wind analysis to evaluate weather system vectors directly from radar metadata.

### Changed
- Reorganized feature documentation and cleaned up the workspace for better maintainability.
- Updated the manual verification guide to reflect the new OCR fallback chain architecture.

### Fixed
- Made Google API imports optional to prevent the server from crashing when dependencies are missing.
- Cached fallback timestamps when OCR fails to read radar frames, preventing repeated failures.

## [0.21.0] - 2026-06-06
### Added
- Implemented an approaching cloud detector with an ETA timeline to track multi-user cloud movement.
- Added visual radar animations (GIFs) and tracking images directly into Telegram webhook and scheduler alerts.
- Added human-readable timestamps and visual growth/decay modeling on the radar loop frames.
- Implemented spatial max dBZ search and lagrangian growth tracking for more robust rain intensity prediction.
- Added various debugging and visualization scripts for flow tracking analysis.

### Changed
- Improved optical flow accuracy via rain masking and densification techniques.
- Enhanced radar GIF visibility by extracting exact timestamps from HTML metadata, increasing font sizes, and adjusting upscale factors.
- Sent separate unoptimized high-quality GIFs as Telegram documents alongside optimized animations for better user experience.

### Fixed
- Fixed Telegram text API and GIF upload timeouts by increasing request limits and correcting MIME types.
- Fixed UI clutter on radar tracking images by removing unnecessary search radii, zooming into user locations, and limiting displayed clouds.
- Fixed `NameError` and frame-freezing bugs during timeline and radar generation.

## [0.20.0] - 2026-06-06
### Added
- Implemented optical flow nowcasting and rain extrapolation for TMD radar to predict rain cell movement.
- Added animation loop polling and coordinate calibration for real-time radar data tracking.
- Added dual-mode cropping (static/loop) and azimuthal projection support to maximize coordinate mapping accuracy.

## [0.19.0] - 2026-06-06
### Added
- Implemented an automated TMD radar image processing system to extract real-time rain intensity directly from radar imagery.
- Added live intensity testing and improved mapping accuracy for TMD radar coordinates.

### Changed
- Updated radar station configurations (`kkn120`, `kkn240`, `skn240`) and adjusted their default reliability scores within the auto-fallback system.

### Fixed
- Fixed a bug in the webhook output formatter where the current rain intensity from TMD radar was incorrectly ignored due to a lack of minute-by-minute predictions.

## [0.18.0] - 2026-06-05
### Added
- Integrated Open-Meteo as a contingency service for predicting wind vectors and stormcells.
- Implemented a feedback-driven API reliability and auto-selection system that automatically prioritizes the most accurate weather source based on user reports.
- Added API accuracy evaluation scores to the Telegram 'Compare API' functionality.

### Changed
- Refactored WeatherManager fallback logic to dynamically sort APIs based on their accuracy scores.
- Updated API mapping to properly record false alarms from Open-Meteo and Xweather.

## [0.17.0] - 2026-06-05
### Added
- Implemented proactive alerts for major natural hazards including Earthquakes, Tropical Cyclones, and Fires/Hotspots.
- Added a hybrid Earthquake alert system utilizing EMSC WebSockets for real-time pushing and USGS GeoJSON polling for redundancy.
- Added smart broad geofencing logic with event-specific impact radiuses (up to 1,000km) to accurately identify affected users.
- Introduced grouped disaster alerts to consolidate warnings for users with multiple affected saved locations, preventing notification spam.
- Built CLI and HTTP mock testing tools (`mock_emsc_ws.py` and `mock_disasters.py`) for simulating disaster events and validating End-to-End WebSocket functionality.

### Changed
- Refactored disaster alert history tracking to use a Repository pattern, fully supporting both SQLite and Firestore state management across Cloud Run instances to prevent duplicate alerts.
- Updated ADR documentation for Issue Batching Strategy and Terraform Infrastructure as Code.

### Fixed
- Added robust error handling and debug logging to disaster background processing loops.

## [0.16.0] - 2026-06-04
### Added
- Integrated Xweather (Premium) as a primary weather provider for highly accurate minutely precipitation forecasting.
- Added Advanced Weather Alerts capability to proactively warn users about nearby severe weather, including convective stormcells and lightning strikes.
- Expanded weather data telemetry in the Telegram webhook to display precise distance, direction, and speed of incoming storms when detected by Xweather.

### Changed
- Refactored the WeatherManager's fallback chain to gracefully cascade from Xweather to Tomorrow.io and Rainbow APIs in the event of API failures or trial expirations.
- Improved webhook reporting to include explicit API labels, ensuring users know exactly which provider generated the forecast.

### Fixed
- Enhanced Xweather service resilience by implementing a robust circuit breaker handling HTTP 401, 403, and 429 errors automatically.

## [0.15.0] - 2026-06-04
### Added
- Implemented cancellation (All-Clear) alerts to notify users when previously forecasted rain dissipates before reaching them.
- Added interactive API Comparison feature allowing users to view raw forecast data from all 3 sources (Tomorrow.io, Rainbow Local, Rainbow Global) directly via inline buttons.
- Introduced interactive Ground Truth Feedback allowing users to report false alarms directly from notifications, storing precise API context and max rain parameters for future AI training.
- Added explicit "last updated" timestamps to both the initial alert and the comparison messages.

### Fixed
- Fixed an issue where saving user feedback failed silently on Firestore due to incompatible naive datetime objects in the Python SDK.

## [0.14.0] - 2026-06-04
### Added
- Implemented an immediate "loading" state in the Telegram webhook using background tasks to prevent API timeouts and improve responsiveness (Issue #37).
- Added a "Smart Cooldown" feature that overrides active alert cooldowns if rain severity escalates (Issue #26).

### Changed
- Refactored Telegram webhook to utilize the `WeatherManager` fallback chain directly, ensuring consistent weather data processing (Issue #38).

### Fixed
- Fixed an issue where the Rainbow.ai API client swallowed HTTP exceptions, which prevented the fallback chain from activating.
- Corrected Telegram bot message rendering to show a proper error message when all weather APIs fail, instead of incorrectly reporting no rain.

## [0.13.0] - 2026-06-03
### Added
- Integrated Tomorrow.io weather service as the primary data source for hyper-local rain forecasting.
- Implemented a robust fallback mechanism that automatically switches to Rainbow.ai (Local/Global) if the primary service fails.
- Added a threshold filter to suppress false positive rain alerts for very light rain (e.g., < 0.5 mm/hr).
- Enhanced Telegram alert messages to include precise start/end times, rain duration, and estimated cloud distance.

### Changed
- Improved weather service architecture to support multiple interchangeable API engines seamlessly.
- Refactored repository interfaces to increase flexibility and maintainability.

## [0.12.0] - 2026-06-02
### Added
- Supported saving multiple locations per user (e.g., Home, Work, Default).
- Implemented a Developer Mock Mode (`/devmock`) for simulating weather states during scheduler testing.
- Added configurable alert cooldown via environment variables (`ALERT_COOLDOWN_MINUTES`).

### Changed
- Refactored location handling to ensure backward compatibility with legacy single-location data formats.

## [0.11.0] - 2026-06-02
### Changed
- Migrated active alert locations storage from in-memory SQLite to Google Cloud Firestore to prevent data loss during Cloud Run cold starts.

## [0.10.0] - 2026-06-01
### Changed
- Replaced the internal `APScheduler` background task with a dedicated Webhook Endpoint (`/api/v1/cron/check-rain`) to allow integration with external cron services (e.g., Google Cloud Scheduler) and prevent scheduling conflicts across Cloud Run instances.

## [0.9.0] - 2026-05-30
### Changed
- Updated `RainbowService` to integrate with the official Rainbow Weather Nowcast API endpoint (`/precip-global`), ensuring accurate minute-by-minute rain data parsing.

## [0.8.0] - 2026-05-30
### Added
- Implemented GitLab CI/CD pipeline for automated deployment to Google Cloud Run and dynamic Telegram Webhook management.
- Enhanced meteorological alerts to include real-time rain intensity and estimated duration calculations.
- Created documentation for the "Two Bots Strategy" to separate local development and production environments.

### Fixed
- Resolved a logic error in rain duration calculation for single-interval predictions.

### Security
- Updated Cloud Run deployment pipeline to use Base64 encoded Service Account credentials for enhanced security.

## [0.7.0] - 2026-05-30
### Added
- Expanded interactive radar options in Telegram by adding multiple data source links (Zoom Earth, Windy, TMD Radar) to proactive alerts and the `/radar` command.
- Added a developer-specific feature to export and view raw rain prediction data (JSON) directly within Telegram via inline keyboards.

## [0.6.0] - 2026-05-30
### Added
- Implemented the Repository pattern (`sqlite`, `firestore`) and scheduler abstraction to support flexible backend environments.
- Added containerization support (`Dockerfile`) for deploying the FastAPI backend natively to Google Cloud Run.
- Enhanced Telegram webhook functionality with new user commands and interactive responses.
- Appended real-time radar tracking links (Zoom Earth) to proactive rain alert messages.
- Added comprehensive agent skills and infrastructure configuration documentation.

### Changed
- Migrated Firebase Cloud Functions logic into the `backend/` directory, providing a robust wrapper for running FastAPI within Google Cloud serverless environments.

## [0.5.0] - 2026-05-30
### Added
- Implemented background task scheduler (`APScheduler`) integrated with FastAPI lifespan for proactive rain alerts.
- Added database tracking for the last alerted timestamp to prevent notification spam (2-hour cooldown).
- Created a background polling service (`check_rain_and_alert`) that verifies active locations every 5 minutes.

## [0.4.0] - 2026-05-30
### Added
- Implemented user location persistence with SQLite to support proactive alerts.
- Added Telegram inline keyboards for users to save or delete their locations easily.
- Added `/mylocation` command for users to check and manage their saved location and retention policy.

## [0.3.0] - 2026-05-29
### Added
- Implemented Telegram webhook (`POST /api/v1/webhook/telegram`) for on-demand rain notifications.
- Added background task processing for Telegram location payloads and ETA calculation.
- Added comprehensive unit tests for the webhook router.

## [0.2.0] - 2026-05-29
### Added
- Implemented FastAPI on-demand weather prediction endpoints (`GET /api/v1/weather/predict`).
- Added Pydantic schemas for data validation and API response formatting.
- Configured FastAPI `main.py` entrypoint with a health check route.
- Added automated unit tests for the FastAPI routers using `TestClient`.

## [0.1.0] - 2026-05-29
### Added
- Defined `BaseWeatherService` abstract class for pluggable weather providers.
- Implemented `RainViewerService` for fetching recent radar frames.
- Implemented `RainbowService` for fetching raw nowcast predictions.
- Set up tests with `pytest` utilizing Test-Driven Development (TDD).
- Initialized FastAPI project folder structure (`services`, `routers`, `schemas`).
