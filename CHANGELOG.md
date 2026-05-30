# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
