# FonMaYang 🌧️

Privacy-first short-term rain forecasting (Nowcasting) system using Thai Meteorological Department (TMD) radar data and global weather APIs.

## Overview
FonMaYang integrates with multiple weather sources (Xweather, Tomorrow.io, Open-Meteo, RainViewer, Rainbow API, TMD Radar) to predict incoming rain within the next 15-30 minutes. The system operates on a privacy-first principle: no continuous background location tracking. Users opt-in by sharing their current location via Telegram, and the system evaluates the coarse location against the predicted rain vectors.

## Features
- **Pluggable Architecture**: Easily switch between or combine weather providers (Xweather, Tomorrow.io, Open-Meteo, RainViewer, Rainbow, TMD Radar) with an automated fallback mechanism based on user feedback and reliability scoring.
- **Automated TMD Radar Processing**: Real-time extraction of rain intensity directly from TMD radar imagery, fully integrated as a highly accurate data source in the automated fallback system.
- **Natural Hazard Alerts**: Proactive monitoring for severe natural disasters including Earthquakes (via real-time EMSC WebSockets & USGS polling), Tropical Cyclones, and Wildfires, complete with broad geofencing and grouped notifications for users with multiple locations.
- **Advanced Weather Alerts**: Proactively warns users about nearby severe weather, including convective stormcells and lightning strikes, using Xweather's premium data and Open-Meteo contingency data.
- **Privacy-First Notifications**: On-demand location sharing via Telegram without background tracking.
- **Multiple Saved Locations**: Support for managing multiple user locations (e.g., Home, Work) for personalized proactive alerting.
- **Extended Meteorological Data**: Real-time evaluation of rain intensity and estimated duration.
- **Proactive Alerts & Scheduling**: Webhook endpoint designed for external cron services to continuously monitor rain vectors and alert users proactively before rain hits. Includes a Smart Cooldown system with severity escalation.
- **Responsive Webhooks**: Background task processing ensures immediate acknowledgment and loading states for users even during slow API fetching.
- **Interactive Ground Truth Feedback**: Inline buttons allowing users to report false alarms directly from notifications. This data feeds an automated API reliability system that auto-selects the most accurate weather source for future alerts.
- **API Comparison & All-Clear Alerts**: Real-time comparison across all integrated weather APIs and automated cancellation notifications when forecasted rain dissipates.
- **Interactive Radar**: Telegram `/radar` command providing multi-source visual tracking (Zoom Earth, Windy, TMD).
- **Developer Mock Mode**: Built-in `/devmock` command and mock event servers for simulating weather states and natural disasters during testing without making live API calls.
- **FastAPI Backend**: Asynchronous, highly concurrent backend structure.
- **Cloud Run Native**: Fully containerized and automated deployment to Google Cloud Run via GitLab CI/CD pipelines.

## Data Sources
- **Xweather API**: [xweather.com](https://www.xweather.com/)
- **Tomorrow.io API**: [tomorrow.io](https://www.tomorrow.io/)
- **Open-Meteo API**: [open-meteo.com](https://open-meteo.com/)
- **TMD Radar (Khon Kaen, Sakon Nakhon)**: [weather.tmd.go.th](https://weather.tmd.go.th/)
- **RainViewer API**: [api.rainviewer.com/public/weather-maps.json](https://api.rainviewer.com/public/weather-maps.json)
- **Rainbow Weather API**: [api.rainbow.ai](https://api.rainbow.ai/)
- **EMSC Seismic Portal**: [seismicportal.eu](https://www.seismicportal.eu/)
- **USGS Earthquake Hazards Program**: [earthquake.usgs.gov](https://earthquake.usgs.gov/)

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
3. Set up your `.env` file with your `TELEGRAM_BOT_TOKEN`, `TOMORROW_API_KEY`, `RAINBOW_API_KEY`, `XWEATHER_CLIENT_ID`, `XWEATHER_CLIENT_SECRET`, `CRON_SECRET`, etc.
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
