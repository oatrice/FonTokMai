# Roadmap

This document outlines the strategic goals, planned features, and upcoming milestones for the FonTokMai project.

## Phase 1: MVP (Current)
- [x] Pluggable architecture base (`BaseWeatherService`)
- [x] RainViewer integration
- [x] Rainbow API integration
- [ ] Notification routing via Line OA and Telegram
- [ ] Smart Location Request UI
- [ ] Celery/APScheduler setup for polling weather data every 5-10 minutes

## Phase 2: Core Enhancements
- [ ] Direct TMD Radar Image Processing using OpenCV Optical Flow.
- [ ] Geo-referencing pixels to Lat/Lng vectors for precise predictions.
- [ ] Advanced Caching layer with Redis to limit redundant processing.
- [ ] Diff comparison logic between RainViewer and Rainbow predictions.

## Phase 3: Frontend & Web App
- [ ] Next.js Web App with Leaflet.js/Mapbox overlays.
- [ ] Progressive Web App (PWA) capabilities.
- [ ] English Localization (Phase 1 MVP is Thai).

## Phase 4: Mobile App & Expansion
- [ ] Flutter Mobile App development.
- [ ] Support for additional TMD radar stations beyond Sakon Nakhon.
- [ ] Community-based real-time rain reporting (Crowdsourcing).

## Synced From GitHub
### Issue #12 - Feature: Add multiple radar sources (TMD, etc.) to Telegram /radar command
- **GitHub:** [#12](https://gitlab.com/oatricedev/Luma/-/issues/12)
- **Status:** 🟢 **Ready**

### Issue #11 - Feature: Integrate Real Weather API (Tomorrow.io / OpenWeatherMap)
- **GitHub:** [#11](https://gitlab.com/oatricedev/Luma/-/issues/11)
- **Status:** 🟢 **Ready**

### Issue #10 - Infrastructure: Deploy FonTokMai MVP to Production
- **GitHub:** [#10](https://gitlab.com/oatricedev/Luma/-/issues/10)
    - ✅ **Done** (0.6.0)

### Issue #9 - Feature: Support multiple saved locations per user (e.g. Home, Work)
- **GitHub:** [#9](https://gitlab.com/oatricedev/Luma/-/issues/9)
- **Status:** 🟢 **Ready**

### Issue #8 - Infrastructure: Develop Cross-Platform Mobile App (Flutter/React Native)
- **GitHub:** [#8](https://gitlab.com/oatricedev/Luma/-/issues/8)
- **Status:** 🟢 **Ready**

### Issue #7 - Feature: Broad Geofencing and District-Level Alert System
- **GitHub:** [#7](https://gitlab.com/oatricedev/Luma/-/issues/7)
- **Status:** 🟢 **Ready**

### Issue #6 - Feature: User Location Persistence with Expiry (Retention Policy)
- **GitHub:** [#6](https://gitlab.com/oatricedev/Luma/-/issues/6)
    - ✅ **Done** (0.4.0)

### Issue #5 - Integrate Notification Services for Line OA
- **GitHub:** [#5](https://gitlab.com/oatricedev/Luma/-/issues/5)
- **Status:** 🟢 **Ready**

### Issue #4 - Implement Background Task Scheduler for automated polling
- **GitHub:** [#4](https://gitlab.com/oatricedev/Luma/-/issues/4)
    - ✅ **Done** (0.5.0)

### Issue #3 - Integrate Notification Services (Line OA / Telegram)
- **GitHub:** [#3](https://gitlab.com/oatricedev/Luma/-/issues/3)
    - ✅ **Done** (0.3.0)

### Issue #2 - Implement FastAPI On-demand Routers for RainNowcast
- **GitHub:** [#2](https://gitlab.com/oatricedev/Luma/-/issues/2)
    - ✅ **Done** (0.2.0)

### Issue #1 - Implement Weather Services MVP (Base, RainViewer, Rainbow) with TDD
- **GitHub:** [#1](https://gitlab.com/oatricedev/Luma/-/issues/1)
- **Status:** 🟢 **Ready**


### Issue # - Implement Weather Services MVP (Base, RainViewer, Rainbow) with TDD
- **State:** opened
- ✅ **Done** (0.1.0)

