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
### Issue #42 - feat: Insights API Comparison (แสดงข้อมูลเทียบทุกค่าย)
- **GitHub:** [#42](https://gitlab.com/oatricedev/FonMaYang/-/issues/42)
- **Status:** 🟢 **Ready**

### Issue #41 - feat: Cancellation / All-Clear Alert (แจ้งเตือนฝนหยุด/เปลี่ยนทิศ)
- **GitHub:** [#41](https://gitlab.com/oatricedev/FonMaYang/-/issues/41)
- **Status:** 🟢 **Ready**

### Issue #40 - Feature: AI Training via Radar Image / JSON Uploads
- **GitHub:** [#40](https://gitlab.com/oatricedev/FonMaYang/-/issues/40)
- **Status:** 🟢 **Ready**

### Issue #39 - Feature: Interactive Ground Truth Feedback (Crowdsourcing)
- **GitHub:** [#39](https://gitlab.com/oatricedev/FonMaYang/-/issues/39)
- **Status:** 🟢 **Ready**

### Issue #38 - Tech Debt: Refactor Telegram Webhook to use WeatherManager (Fix Inconsistency)
- **GitHub:** [#38](https://gitlab.com/oatricedev/FonMaYang/-/issues/38)
    - ✅ **Done** (0.14.0)

### Issue #37 - Feature: Immediate Reply/Loading State on User Input
- **GitHub:** [#37](https://gitlab.com/oatricedev/FonMaYang/-/issues/37)
    - ✅ **Done** (0.14.0)

### Issue #36 - Feature: Telegram Mini App - Live Weather Map
- **GitHub:** [#36](https://gitlab.com/oatricedev/FonMaYang/-/issues/36)
- **Status:** 🟢 **Ready**

### Issue #35 - Feature: Storm Cell Tracking & ETA (Advanced Nowcasting)
- **GitHub:** [#35](https://gitlab.com/oatricedev/FonMaYang/-/issues/35)
- **Status:** 🟢 **Ready**

### Issue #34 - Feature: Lightning Proximity Alerts
- **GitHub:** [#34](https://gitlab.com/oatricedev/FonMaYang/-/issues/34)
- **Status:** 🟢 **Ready**

### Issue #33 - Feature: Severe Weather & Flood Alerts via Xweather
- **GitHub:** [#33](https://gitlab.com/oatricedev/FonMaYang/-/issues/33)
- **Status:** 🟢 **Ready**

### Issue #32 - Feature: Integrate Xweather as a Premium Weather Provider
- **GitHub:** [#32](https://gitlab.com/oatricedev/FonMaYang/-/issues/32)
- **Status:** 🟢 **Ready**

### Issue #31 - Feature: Wind Vector Nowcasting — Calculate Storm Cell Movement Trajectory Before Alerting
- **GitHub:** [#31](https://gitlab.com/oatricedev/FonMaYang/-/issues/31)
- **Status:** 🟢 **Ready**

### Issue #30 - Improvement: Tighten Geofence Radius to 5-10 km to Isolate Local Weather from Cross-border Events
- **GitHub:** [#30](https://gitlab.com/oatricedev/FonMaYang/-/issues/30)
- **Status:** 🟢 **Ready**

### Issue #29 - Improvement: Raise Rain Alert Threshold to Filter Noise and False Buffers
- **GitHub:** [#29](https://gitlab.com/oatricedev/FonMaYang/-/issues/29)
    - ✅ **Done** (0.13.0)

### Issue #28 - Feature: Switch to RainViewer Radar API for Real-time Local dBZ Reflectivity
- **GitHub:** [#28](https://gitlab.com/oatricedev/FonMaYang/-/issues/28)
- **Status:** 🟢 **Ready**

### Issue #27 - Bug: False Positive Rain Alert caused by Coarse Global Forecast Model (Cross-border Storm Bleed)
- **GitHub:** [#27](https://gitlab.com/oatricedev/FonMaYang/-/issues/27)
- **Status:** 🟢 **Ready**

### Issue #26 - Feature: Smart Cooldown (Escalation Alert) for Background Scheduler
- **GitHub:** [#26](https://gitlab.com/oatricedev/FonMaYang/-/issues/26)
    - ✅ **Done** (0.14.0)

### Issue #25 - Refactor: Replace APScheduler with external cron service and webhook endpoint
- **GitHub:** [#25](https://gitlab.com/oatricedev/FonMaYang/-/issues/25)
    - ✅ **Done** (0.10.0)

### Issue #24 - Enhancement: Format rain duration from minutes to hours and minutes
- **GitHub:** [#24](https://gitlab.com/oatricedev/FonMaYang/-/issues/24)
    - ✅ **Done** (0.13.0)

### Issue #23 - Feature/UX: Reconcile discrepancies between Global and Local Radar rain predictions
- **GitHub:** [#23](https://gitlab.com/oatricedev/FonMaYang/-/issues/23)
- **Status:** 🟢 **Ready**

### Issue #22 - Bug: Telegram answerCallbackQuery fails with 400 Bad Request during cold starts
- **GitHub:** [#22](https://gitlab.com/oatricedev/FonMaYang/-/issues/22)
- **Status:** 🟢 **Ready**

### Issue #21 - Bug: Active alert locations are lost during Cloud Run cold start (State Loss)
- **GitHub:** [#21](https://gitlab.com/oatricedev/FonMaYang/-/issues/21)
    - ✅ **Done** (0.11.0)

### Issue #20 - Feature: Detailed Chat Alert (Start/End Time, Duration, Cloud Distance)
- **GitHub:** [#20](https://gitlab.com/oatricedev/FonMaYang/-/issues/20)
    - ✅ **Done** (0.13.0)

### Issue #19 - Feature: Developer Mock Mode for Background Scheduler
- **GitHub:** [#19](https://gitlab.com/oatricedev/FonMaYang/-/issues/19)
    - ✅ **Done** (0.12.0)

### Issue #18 - Dummy for test
- **GitHub:** [#18](https://gitlab.com/oatricedev/Luma/-/issues/18)
- **Status:** 🟢 **Ready**

### Issue #17 - Update RainbowService to use official Rainbow Weather Nowcast API
- **GitHub:** [#17](https://gitlab.com/oatricedev/Luma/-/issues/17)
    - ✅ **Done** (0.9.0)

### Issue #16 - Feature: Integrate external meteorological APIs (Open-Meteo, TMD) for enhanced data (Wind, Accurate Intensity)
- **GitHub:** [#16](https://gitlab.com/oatricedev/Luma/-/issues/16)
- **Status:** 🟢 **Ready**

### Issue #15 - Infrastructure: CI/CD Auto-deploy to Cloud Run and Webhook Management
- **GitHub:** [#15](https://gitlab.com/oatricedev/Luma/-/issues/15)
    - ✅ **Done** (0.8.0)

### Issue #14 - Feature Research: Rain Prediction along Driving Route (Route vs Live Tracking)
- **GitHub:** [#14](https://gitlab.com/oatricedev/Luma/-/issues/14)
- **Status:** 🟢 **Ready**

### Issue #13 - Feature: Enhance Rain Alert with Extended Meteorological Data (Intensity, Duration, Wind)
- **GitHub:** [#13](https://gitlab.com/oatricedev/Luma/-/issues/13)
    - ✅ **Done** (0.13.0)

### Issue #12 - Feature: Add multiple radar sources (TMD, etc.) to Telegram /radar command
- **GitHub:** [#12](https://gitlab.com/oatricedev/Luma/-/issues/12)
    - ✅ **Done** (0.7.0)

### Issue #11 - Feature: Integrate Real Weather API (Tomorrow.io / OpenWeatherMap)
- **GitHub:** [#11](https://gitlab.com/oatricedev/Luma/-/issues/11)
    - ✅ **Done** (0.13.0)

### Issue #10 - Infrastructure: Deploy FonTokMai MVP to Production
- **GitHub:** [#10](https://gitlab.com/oatricedev/Luma/-/issues/10)
    - ✅ **Done** (0.6.0)

### Issue #9 - Feature: Support multiple saved locations per user (e.g. Home, Work)
- **GitHub:** [#9](https://gitlab.com/oatricedev/Luma/-/issues/9)
    - ✅ **Done** (0.12.0)

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

