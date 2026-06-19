# FonMaYang 🌧️

Privacy-first short-term rain forecasting (Nowcasting) system using Thai Meteorological Department (TMD) radar data and global weather APIs.

## Overview
FonMaYang integrates with multiple weather sources (Xweather, Tomorrow.io, Open-Meteo, RainViewer, Rainbow API, TMD Radar) to predict incoming rain within the next 15-30 minutes. The system operates on a privacy-first principle: no continuous background location tracking. Users opt-in by sharing their current location via Telegram, and the system evaluates the coarse location against the predicted rain vectors.

## Features
- **Pluggable Architecture**: Easily switch between or combine weather providers (Xweather, Tomorrow.io, Open-Meteo, RainViewer, Rainbow, TMD Radar) with an automated fallback mechanism based on user feedback and reliability scoring.
- **Automated TMD Radar Processing & Nowcasting**: Real-time extraction of rain intensity directly from TMD radar imagery, fully integrated as a highly accurate data source in the automated fallback system. Includes optical flow extrapolation, azimuthal projection, and a unified Firebase Storage/Firestore caching system (`radar_latest_cache`) for precise rain cell tracking, forecasting, and high-concurrency rate-limit prevention using efficient static frame comparisons.
- **Resilient Radar OCR Pipeline**: Utilizes an automated fallback chain (Google Cloud Vision -> Gemini -> OCR.space) for reliable radar timestamp extraction, safeguarded by a Firestore-based quota management system.
- **Visual Radar Tracking & ETA Timelines**: Generates and sends high-quality radar animation loops (GIFs), tracked cloud visualizations, and human-readable ETA confidence timelines directly to users via Telegram webhooks and scheduled alerts.
- **Advanced Lagrangian Cloud Modeling**: Employs spatial max dBZ search and lagrangian tracking to model rain cell growth, decay, and precise movement paths across multi-user environments.
- **Natural Hazard Alerts**: Proactive monitoring for severe natural disasters including Earthquakes (via a decoupled standalone EMSC WebSocket worker & USGS polling), Tropical Cyclones, and Wildfires, complete with broad geofencing and grouped notifications for users with multiple locations.
- **Advanced Weather Alerts**: Proactively warns users about nearby severe weather, including convective stormcells and lightning strikes, using Xweather's premium data and Open-Meteo contingency data. Includes the `/rain_pro` manual command for on-demand premium reports.
- **Privacy-First Notifications**: On-demand location sharing via Telegram without background tracking.
- **Multiple Saved Locations**: Support for managing multiple user locations (e.g., Home, Work) for personalized proactive alerting.
- **Extended Meteorological Data**: Real-time evaluation of rain intensity and estimated duration.
- **Proactive Alerts & Scheduling**: Webhook endpoint designed for external cron services to continuously monitor rain vectors and alert users proactively before rain hits. Includes a Smart Cooldown system with severity escalation. Concurrent alert processing is highly modularized via asyncio semaphores.
- **Responsive Webhooks**: Optimized inline request processing to ensure immediate acknowledgment and prevent Cloud Run CPU throttling during slow API fetches.
- **System Telemetry & Metrics**: Includes lightweight telemetry and a secured internal API endpoint for exporting Cloud Run and scheduled routine metrics for performance analysis. Internal worker endpoints are protected by token-based authentication.
- **Interactive Ground Truth Feedback**: Inline buttons allowing users to report false alarms directly from notifications. This data feeds an automated API reliability system that auto-selects the most accurate weather source for future alerts.
- **API Comparison & All-Clear Alerts**: Real-time comparison across all integrated weather APIs and automated cancellation notifications when forecasted rain dissipates.
- **Interactive Radar**: Telegram `/radar` command providing multi-source visual tracking (Zoom Earth, Windy, TMD).
- **Developer Mock Mode**: Built-in `/devmock` command and standalone mock event servers (including a local WebSocket mock server) for simulating weather states, API fallback errors, and natural disasters during testing without making live API calls.
- **Asynchronous Workload Queuing**: Deep integration with Google Cloud Tasks to offload long-running radar and forecasting processes, preventing Cloud Run CPU throttling and ensuring reliable delivery with exponential backoff.
- **Budget Auto-Shutdown Mechanism**: Native GCP Billing Budget integration with Pub/Sub webhooks to automatically revoke Cloud Run public access when spending limits are reached, preventing unexpected billing spikes.
- **Cost-Optimized Cloud Logging**: Pre-configured Logging Exclusion filters to drop high-frequency debug noise, drastically reducing log ingestion costs.
- **FastAPI Backend**: Asynchronous, highly concurrent backend structure.
- **Cloud Run Native**: Fully containerized and automated deployment to Google Cloud Run via GitHub Actions CI/CD pipelines (Scale-to-zero optimized).

## Usage & Commands

To use the bot, simply **Share your Location** via Telegram to register your coordinates. The system will then be able to provide accurate rain nowcasts for your area.

### User Commands
- **`/rain [provider] [location]`** - Check the current short-term rain forecast. Both `provider` and `location` are optional and can be in any order.
- **`/rain_pro [provider] [location]`** - Check the rain forecast along with premium advanced alerts (Severe Thunderstorms, Lightning distance, Stormcell movements).
- **`/check`** - A quick shorthand alias for `/rain tmd-radar`.
- **`/radar`** - View interactive radar maps (Zoom Earth, Windy, TMD) for your location.
- **`/mylocation`** - Check your currently saved location coordinates and their names (e.g., Home, Work) in the system.

#### Command Arguments:
You can append arguments to `/rain` or `/rain_pro` to target specific data:
- **`[location]`**: If you have multiple locations saved, type the name to check it specifically. 
  - *Example:* `/rain home`, `/rain_pro work`
- **`[provider]`**: Force the bot to bypass the auto-selection and use a specific weather API. Supported providers:
  - `tmd-radar` (or `tmd`): Real-time rain intensity and ETA extracted directly from Thai Meteorological Department radar images. Extremely accurate for incoming rain cells.
  - `xweather`: Premium data source. Excellent for advanced storm tracking, lightning strikes, and severe weather advisories.
  - `tomorrow`: Highly accurate minute-by-minute forecasting.
  - `open-meteo`: Fast and reliable open-source weather data. Often used as a robust fallback.
  - `rainbow-local` / `rainbow-global`: Uses Rainbow.ai's AI-driven localized or global nowcasting models.
  - *Example:* `/rain xweather`, `/rain work tomorrow`

### Developer Mock Commands
Used for testing alerts and system behaviors without waiting for real weather events:
- **`/devmock rain`** - Simulates an incoming rain storm to test radar image generation and standard alerts.
- **`/devmock storm`** - Simulates a severe storm across the entire radar frame.
- **`/devmock error`** - Simulates an API failure to test the fallback mechanisms and circuit breakers.
- **`/devmock clear`** - Simulates clear skies with no rain.
- **`/devmock off`** - Turns off mock mode and returns to live data.

## Data Sources
- **Xweather API**: [xweather.com](https://www.xweather.com/)
- **Tomorrow.io API**: [tomorrow.io](https://www.tomorrow.io/)
- **Open-Meteo API**: [open-meteo.com](https://open-meteo.com/)
- **TMD Radar (Khon Kaen, Sakon Nakhon)**: [weather.tmd.go.th](https://weather.tmd.go.th/)
- **RainViewer API**: [api.rainviewer.com/public/weather-maps.json](https://api.rainviewer.com/public/weather-maps.json)
- **Rainbow Weather API**: [api.rainbow.ai](https://api.rainbow.ai/)
- **EMSC Seismic Portal**: [seismicportal.eu](https://www.seismicportal.eu/)
- **USGS Earthquake Hazards Program**: [earthquake.usgs.gov](https://earthquake.usgs.gov/)
- **Google Cloud Vision / Gemini APIs**: [cloud.google.com](https://cloud.google.com/)
- **OCR.space API**: [ocr.space](https://ocr.space/)

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
3. Set up your `.env` file with your `TELEGRAM_BOT_TOKEN`, `TOMORROW_API_KEY`, `RAINBOW_API_KEY`, `XWEATHER_CLIENT_ID`, `XWEATHER_CLIENT_SECRET`, `CRON_SECRET`, `GEMINI_API_KEY`, `OCR_SPACE_API_KEY`, etc.
4. Run unit tests:
   ```bash
   pytest tests/
   ```
5. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8081
   ```
   *For local Telegram webhook testing, use [localtunnel](https://github.com/localtunnel/localtunnel) to expose port 8081. See `docs/development_guide.md` for details on the Two Bots Strategy.*

### Deployment (GitHub Actions -> Google Cloud Run)
Deployment is handled automatically by GitHub Actions. Pushing to the `main` branch triggers a build and deploy process using the `Dockerfile` in the `backend/` directory, updating the Telegram Webhook automatically to the new Cloud Run URL.
