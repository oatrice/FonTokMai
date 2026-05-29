# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
