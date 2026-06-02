# FonMaYang 🌧️

Privacy-first short-term rain forecasting (Nowcasting) system using Thai Meteorological Department (TMD) radar data and global weather APIs.

## Overview
FonMaYang integrates with multiple weather sources (RainViewer, Rainbow API) to predict incoming rain within the next 15-30 minutes. The system operates on a privacy-first principle: no continuous background location tracking. Users opt-in by sharing their current location via Telegram, and the system evaluates the coarse location against the predicted rain vectors.

## Features
- **Pluggable Architecture**: Easily switch between or combine weather providers (RainViewer, Rainbow, TMD Radar).
- **Privacy-First Notifications**: On-demand location sharing via Telegram without background tracking.
- **Multiple Saved Locations**: Support for managing multiple user locations (e.g., Home, Work) for personalized proactive alerting.
- **Extended Meteorological Data**: Real-time evaluation of rain intensity and estimated duration.
- **Proactive Alerts & Scheduling**: Webhook endpoint designed for external cron services to continuously monitor rain vectors and alert users proactively before rain hits. Includes a configurable alert cooldown.
- **Interactive Radar**: Telegram `/radar` command providing multi-source visual tracking (Zoom Earth, Windy, TMD).
- **Developer Mock Mode**: Built-in `/devmock` command for simulating weather states during testing without making live API calls.
- **FastAPI Backend**: Asynchronous, highly concurrent backend structure.
- **Cloud Run Native**: Fully containerized and automated deployment to Google Cloud Run via GitLab CI/CD pipelines.

## Data Sources
- **TMD Radar (Sakon Nakhon)**: [weather.tmd.go.th/sknLoop.php](https://weather.tmd.go.th/sknLoop.php)
- **RainViewer API**: [api.rainviewer.com/public/weather-maps.json](https://api.rainviewer.com/public/weather-maps.json)
- **Rainbow Weather API**: [api.rainbow.ai](https://api.rainbow.ai/)

## Getting Started

### Prerequisites
- Python 3.9+
- Docker (optional, for Cloud Run deployment)

### Local Development
1. Clone the repository
2. Install dependencies:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Set up your `.env` file with your `TELEGRAM_BOT_TOKEN`, `RAINBOW_API_KEY`, `CRON_SECRET`, etc.
4. Run unit tests:
   ```bash
   pytest tests/
   ```
5. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8080
   ```
   *For local Telegram webhook testing, use [localtunnel](https://github.com/localtunnel/localtunnel) to expose port 8080. See `docs/development_guide.md` for details on the Two Bots Strategy.*

### Deployment (GitLab CI -> Google Cloud Run)
Deployment is handled automatically by GitLab CI. Pushing to the `main` branch triggers a build and deploy process using the `Dockerfile` in the `backend/` directory, updating the Telegram Webhook automatically to the new Cloud Run URL.
