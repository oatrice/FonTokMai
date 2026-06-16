# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
