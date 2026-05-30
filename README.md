# FonMaYang 🌧️

Privacy-first short-term rain forecasting (Nowcasting) system using Thai Meteorological Department (TMD) radar data.

## Overview
FonMaYang integrates with multiple weather sources (RainViewer, Rainbow API) to predict incoming rain within the next 15-30 minutes. The system operates on a privacy-first principle: no continuous background location tracking. Users opt-in by sharing their current location via Line OA or Telegram, and the system evaluates the coarse location against the predicted rain vectors.

## Features
- **Pluggable Architecture**: Easily switch between or combine weather providers (RainViewer, Rainbow, TMD Radar).
- **Flexible Infrastructure**: Implemented Repository pattern for seamless switching between local SQLite and production Firestore databases.
- **Privacy-First Notifications**: On-demand location sharing via Line/Telegram without background tracking.
- **Data Quality Monitoring**: Actively monitors upstream radar data latency and pauses alerts if the source is outdated (> 30 mins).
- **FastAPI Backend**: Asynchronous, highly concurrent backend structure, containerized via Docker for easy deployment to Google Cloud Run or Firebase.
- **Proactive Task Scheduler**: Built-in task scheduling (via APScheduler or external Cloud Scheduler) to proactively poll rain data for active users and send automated alerts with interactive radar links.

## Data Sources
- **TMD Radar (Sakon Nakhon)**: [weather.tmd.go.th/sknLoop.php](https://weather.tmd.go.th/sknLoop.php)
- **RainViewer API**: [api.rainviewer.com/public/weather-maps.json](https://api.rainviewer.com/public/weather-maps.json)
- **Rainbow Weather API**: [api.rainbow.ai](https://api.rainbow.ai/)

## Getting Started

### Prerequisites
- Python 3.9+
- Redis (For caching)
- Docker (Optional, for containerized deployment)

### Installation
1. Clone the repository
2. Install dependencies:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Run unit tests:
   ```bash
   pytest tests/
   ```
4. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload
   ```
5. Run manual API test script:
   ```bash
   python3 test_apis.py
   ```
   This scratch script will fetch the latest metadata from RainViewer and prediction data from Rainbow API.
