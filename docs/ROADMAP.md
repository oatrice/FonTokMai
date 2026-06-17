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
### Issue #90 - Optimization: Cleanup stale AI-generated context artifacts and establish ephemeral docs policy
- **GitHub:** [#90](https://gitlab.com/oatricedev/FonMaYang/-/issues/90)
- **Status:** 🟢 **Ready**

### Issue #89 - 🏗 [Architecture] Decouple EMSC WebSocket from Cloud Run API (Long-term Solution)
- **GitHub:** [#89](https://gitlab.com/oatricedev/FonMaYang/-/issues/89)
- **Status:** 🟢 **Ready**

### Issue #88 - 🛠 [Infra] Fix Cloud Scheduler Retry Policy to prevent retry flood
- **GitHub:** [#88](https://gitlab.com/oatricedev/FonMaYang/-/issues/88)
- **Status:** 🟢 **Ready**

### Issue #87 - 🛠 [Infra] Limit Cloud Run max-instances and pause check-rain Scheduler
- **GitHub:** [#87](https://gitlab.com/oatricedev/FonMaYang/-/issues/87)
    - ✅ **Done** (0.30.0)

### Issue #86 - 🛠 [Hotfix] Temporarily disable EMSC WebSocket to prevent Cloud Run Memory Leak
- **GitHub:** [#86](https://gitlab.com/oatricedev/FonMaYang/-/issues/86)
    - ✅ **Done** (0.30.0)

### Issue #85 - 🛠 [Hotfix] Bypass OCR Fallback Trap to reduce Cloud Run latency
- **GitHub:** [#85](https://gitlab.com/oatricedev/FonMaYang/-/issues/85)
    - ✅ **Done** (0.30.0)

### Issue #84 - 🚨 Critical Incident: Memory Leak & Billing Explosion from OCR Fallback & WebSocket
- **GitHub:** [#84](https://gitlab.com/oatricedev/FonMaYang/-/issues/84)
- **Status:** 🟢 **Ready**

### Issue #83 - Optimization: Cleanup old Docker Images in Artifact Registry
- **GitHub:** [#83](https://gitlab.com/oatricedev/FonMaYang/-/issues/83)
- **Status:** 🟢 **Ready**

### Issue #82 - Feature: Manage GCP Budget and Alerts via Terraform (IaC)
- **GitHub:** [#82](https://gitlab.com/oatricedev/FonMaYang/-/issues/82)
- **Status:** 🟢 **Ready**

### Issue #81 - Feature: Adjust GCP Budget via Telegram command (/setbudget)
- **GitHub:** [#81](https://gitlab.com/oatricedev/FonMaYang/-/issues/81)
- **Status:** 🟢 **Ready**

### Issue #80 - Feature: Route billing and system alerts to dedicated DevBot
- **GitHub:** [#80](https://gitlab.com/oatricedev/FonMaYang/-/issues/80)
- **Status:** 🟢 **Ready**

### Issue #79 - Infrastructure: Setup System Uptime Monitoring & Status Dashboard
- **GitHub:** [#79](https://gitlab.com/oatricedev/FonMaYang/-/issues/79)
- **Status:** 🟢 **Ready**

### Issue #78 - Architecture: Implement Dedicated Users (Private Cloud Run) with Reverse Proxy / API Gateway
- **GitHub:** [#78](https://gitlab.com/oatricedev/FonMaYang/-/issues/78)
- **Status:** 🟢 **Ready**

### Issue #76 - Security: Enforce minimal IAM permissions for Cloud Run
- **GitHub:** [#76](https://gitlab.com/oatricedev/FonMaYang/-/issues/76)
    - ✅ **Done** (0.28.0) 

### Issue #77 - Infrastructure: Automate Cloud Scheduler Jobs Migration
- **GitHub:** [#77](https://gitlab.com/oatricedev/FonMaYang/-/issues/77)
    - ✅ **Done** (0.28.0)

### Issue #75 - [Epic] Environment Staging & Automated Secret Management (Local/UAT/PROD)
- **GitHub:** [#75](https://gitlab.com/oatricedev/FonMaYang/-/issues/75)
- **Status:** 🟢 **Ready**

### Issue #74 - Add Cloud Tasks Queue Monitoring & API endpoint
- **GitHub:** [#74](https://gitlab.com/oatricedev/FonMaYang/-/issues/74)
- **Status:** 🟢 **Ready**

### Issue #73 - Verify Performance Gains & Monitor Memory Usage Post-Deployment of #71
- **GitHub:** [#73](https://gitlab.com/oatricedev/FonMaYang/-/issues/73)
- **Status:** 🟢 **Ready**

### Issue #72 - Feature: Budget-based Auto-shutdown Mechanism for Cloud Run
- **GitHub:** [#72](https://gitlab.com/oatricedev/FonMaYang/-/issues/72)
    - ✅ **Done** (0.29.0)

### Issue #71 - Optimize Cloud Storage Fetching & Remove Blocking I/O in Radar Processor
- **GitHub:** [#71](https://gitlab.com/oatricedev/FonMaYang/-/issues/71)
    - ✅ **Done** (0.26.0)

### Issue #70 - Feature: Overlay historical wind vectors and timestamps on cropped radar images
- **GitHub:** [#70](https://gitlab.com/oatricedev/FonMaYang/-/issues/70)
- **Status:** 🟢 **Ready**

### Issue #69 - Enhancement: System Infrastructure and Code Optimization (Latency & Billing)
- **GitHub:** [#69](https://gitlab.com/oatricedev/FonMaYang/-/issues/69)
    - ✅ **Done** (0.29.0)

### Issue #68 - Feature: Export metrics via Telegram command (/metrics)
- **GitHub:** [#68](https://gitlab.com/oatricedev/FonMaYang/-/issues/68)
- **Status:** 🟢 **Ready**

### Issue #67 - Feature: Implement build-time versioning and display deployment info in Telegram
- **GitHub:** [#67](https://gitlab.com/oatricedev/FonMaYang/-/issues/67)
- **Status:** 🟢 **Ready**

### Issue #66 - Calculate rain cloud trajectory to improve alert accuracy
- **GitHub:** [#66](https://gitlab.com/oatricedev/FonMaYang/-/issues/66)
    - ✅ **Done** (0.25.0)

### Issue #65 - Refactor: Migrate long-running background tasks to Google Cloud Tasks / PubSub
- **GitHub:** [#65](https://gitlab.com/oatricedev/FonMaYang/-/issues/65)
    - ✅ **Done** (0.29.0)

### Issue #64 - fix: Production bugs on Weather Managers and Open-Meteo integrations
- **GitHub:** [#64](https://gitlab.com/oatricedev/FonMaYang/-/issues/64)
    - ✅ **Done** (0.24.0)

### Issue #63 - Mask API keys and secrets before logging
- **GitHub:** [#63](https://gitlab.com/oatricedev/FonMaYang/-/issues/63)
    - ✅ **Done** (0.24.0)

### Issue #62 - Export Google Cloud Run dashboard metrics for analysis
- **GitHub:** [#62](https://gitlab.com/oatricedev/FonMaYang/-/issues/62)
    - ✅ **Done** (0.26.0)

### Issue #61 - Feature: Digitize and Re-render Radar Images for Higher Sharpness
- **GitHub:** [#61](https://gitlab.com/oatricedev/FonMaYang/-/issues/61)
- **Status:** 🟢 **Ready**

### Issue #60 - Feature: Implement Pre-fetch & Caching for Radar Frame OCR
- **GitHub:** [#60](https://gitlab.com/oatricedev/FonMaYang/-/issues/60)
    - ✅ **Done** (0.22.0)

### Issue #59 - Feature: Relate timeline bar graphs to specific rain clouds in radar image
- **GitHub:** [#59](https://gitlab.com/oatricedev/FonMaYang/-/issues/59)
- **Status:** 🟢 **Ready**

### Issue #58 - Bug: Radar tracking image circles incorrect cloud positions
- **GitHub:** [#58](https://gitlab.com/oatricedev/FonMaYang/-/issues/58)
    - ✅ **Done** (0.23.0)

### Issue #57 - Feature: Implement Cloud Growth and Decay Rate Model for TMD Nowcasting
- **GitHub:** [#57](https://gitlab.com/oatricedev/FonMaYang/-/issues/57)
    - ✅ **Done** (0.21.0)

### Issue #56 - Feature: Display TMD Radar images (Latest & Loop) directly in Telegram
- **GitHub:** [#56](https://gitlab.com/oatricedev/FonMaYang/-/issues/56)
    - ✅ **Done** (0.21.0)

### Issue #55 - Enhancement: Fine-tune TMD Radar Location Mapping Accuracy
- **GitHub:** [#55](https://gitlab.com/oatricedev/FonMaYang/-/issues/55)
    - ✅ **Done** (0.20.0)

### Issue #54 - Feature: Implement Radar Animation Loop and Polling
- **GitHub:** [#54](https://gitlab.com/oatricedev/FonMaYang/-/issues/54)
    - ✅ **Done** (0.20.0)

### Issue #53 - Feature: Include TMD Radar in the Telegram Compare API results
- **GitHub:** [#53](https://gitlab.com/oatricedev/FonMaYang/-/issues/53)
    - ✅ **Done** (0.22.0)

### Issue #52 - Feature: Expand TMD Radar integration to nationwide coverage
- **GitHub:** [#52](https://gitlab.com/oatricedev/FonMaYang/-/issues/52)
- **Status:** 🟢 **Ready**

### Issue #51 - Feature: Telegram command for forcing specific weather data source
- **GitHub:** [#51](https://gitlab.com/oatricedev/FonMaYang/-/issues/51)
    - ✅ **Done** (0.22.0)

### Issue #50 - Feature: Automated TMD Radar Image Processing
- **GitHub:** [#50](https://gitlab.com/oatricedev/FonMaYang/-/issues/50)
    - ✅ **Done** (0.19.0)

### Issue #49 - Research: Evaluation Table comparing Weather Providers (Xweather, Tomorrow.io, Rainbow.ai, TMD Image Processing, Open-Meteo)
- **GitHub:** [#49](https://gitlab.com/oatricedev/FonMaYang/-/issues/49)
    - ✅ **Done** (0.18.0)

### Issue #48 - Contingency: Implement Manual Wind Vector Trajectory (Open-Meteo) if Xweather Expires
- **GitHub:** [#48](https://gitlab.com/oatricedev/FonMaYang/-/issues/48)
    - ✅ **Done** (0.18.0)

### Issue #47 - Infrastructure: Migrate to Terraform & Google Secret Manager
- **GitHub:** [#47](https://gitlab.com/oatricedev/FonMaYang/-/issues/47)
- **Status:** 🟢 **Ready**

### Issue #46 - Feature: Batch I - Interactive Weather Maps & Routing
- **GitHub:** [#46](https://gitlab.com/oatricedev/FonMaYang/-/issues/46)
- **Status:** 🟢 **Ready**

### Issue #45 - Feature: Batch H - Disasters & Natural Hazards Alerts
- **GitHub:** [#45](https://gitlab.com/oatricedev/FonMaYang/-/issues/45)
    - ✅ **Done** (0.17.0)

### Issue #44 - Feature: Batch G - Comprehensive Weather & Air Quality (Daily, AQI)
- **GitHub:** [#44](https://gitlab.com/oatricedev/FonMaYang/-/issues/44)
- **Status:** 🟢 **Ready**

### Issue #42 - feat: Insights API Comparison (แสดงข้อมูลเทียบทุกค่าย)
- **GitHub:** [#42](https://gitlab.com/oatricedev/FonMaYang/-/issues/42)
    - ✅ **Done** (0.15.0)

### Issue #41 - feat: Cancellation / All-Clear Alert (แจ้งเตือนฝนหยุด/เปลี่ยนทิศ)
- **GitHub:** [#41](https://gitlab.com/oatricedev/FonMaYang/-/issues/41)
    - ✅ **Done** (0.15.0)

### Issue #40 - Feature: AI Training via Radar Image / JSON Uploads
- **GitHub:** [#40](https://gitlab.com/oatricedev/FonMaYang/-/issues/40)
- **Status:** 🟢 **Ready**

### Issue #39 - Feature: Interactive Ground Truth Feedback (Crowdsourcing)
- **GitHub:** [#39](https://gitlab.com/oatricedev/FonMaYang/-/issues/39)
    - ✅ **Done** (0.15.0)

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
    - ✅ **Done** (0.16.0)

### Issue #34 - Feature: Lightning Proximity Alerts
- **GitHub:** [#34](https://gitlab.com/oatricedev/FonMaYang/-/issues/34)
    - ✅ **Done** (0.16.0)

### Issue #33 - Feature: Severe Weather & Flood Alerts via Xweather
- **GitHub:** [#33](https://gitlab.com/oatricedev/FonMaYang/-/issues/33)
    - ✅ **Done** (0.16.0)

### Issue #32 - Feature: Integrate Xweather as a Premium Weather Provider
- **GitHub:** [#32](https://gitlab.com/oatricedev/FonMaYang/-/issues/32)
    - ✅ **Done** (0.16.0)

### Issue #31 - Feature: Wind Vector Nowcasting — Calculate Storm Cell Movement Trajectory Before Alerting
- **GitHub:** [#31](https://gitlab.com/oatricedev/FonMaYang/-/issues/31)
- **Status:** 🟢 **Done**

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
- **GitHub:** [#18](https://gitlab.com/oatricedev/FonMaYang/-/issues/18)
- **Status:** 🟢 **Ready**

### Issue #17 - Update RainbowService to use official Rainbow Weather Nowcast API
- **GitHub:** [#17](https://gitlab.com/oatricedev/FonMaYang/-/issues/17)
    - ✅ **Done** (0.9.0)

### Issue #16 - Feature: Integrate external meteorological APIs (Open-Meteo, TMD) for enhanced data (Wind, Accurate Intensity)
- **GitHub:** [#16](https://gitlab.com/oatricedev/FonMaYang/-/issues/16)
- **Status:** 🟢 **Ready**

### Issue #15 - Infrastructure: CI/CD Auto-deploy to Cloud Run and Webhook Management
- **GitHub:** [#15](https://gitlab.com/oatricedev/FonMaYang/-/issues/15)
    - ✅ **Done** (0.8.0)

### Issue #14 - Feature Research: Rain Prediction along Driving Route (Route vs Live Tracking)
- **GitHub:** [#14](https://gitlab.com/oatricedev/FonMaYang/-/issues/14)
- **Status:** 🟢 **Ready**

### Issue #13 - Feature: Enhance Rain Alert with Extended Meteorological Data (Intensity, Duration, Wind)
- **GitHub:** [#13](https://gitlab.com/oatricedev/FonMaYang/-/issues/13)
    - ✅ **Done** (0.13.0)

### Issue #12 - Feature: Add multiple radar sources (TMD, etc.) to Telegram /radar command
- **GitHub:** [#12](https://gitlab.com/oatricedev/FonMaYang/-/issues/12)
    - ✅ **Done** (0.7.0)

### Issue #11 - Feature: Integrate Real Weather API (Tomorrow.io / OpenWeatherMap)
- **GitHub:** [#11](https://gitlab.com/oatricedev/FonMaYang/-/issues/11)
    - ✅ **Done** (0.13.0)

### Issue #10 - Infrastructure: Deploy FonTokMai MVP to Production
- **GitHub:** [#10](https://gitlab.com/oatricedev/FonMaYang/-/issues/10)
    - ✅ **Done** (0.6.0)

### Issue #9 - Feature: Support multiple saved locations per user (e.g. Home, Work)
- **GitHub:** [#9](https://gitlab.com/oatricedev/FonMaYang/-/issues/9)
    - ✅ **Done** (0.12.0)

### Issue #8 - Infrastructure: Develop Cross-Platform Mobile App (Flutter/React Native)
- **GitHub:** [#8](https://gitlab.com/oatricedev/FonMaYang/-/issues/8)
- **Status:** 🟢 **Ready**

### Issue #7 - Feature: Broad Geofencing and District-Level Alert System
- **GitHub:** [#7](https://gitlab.com/oatricedev/FonMaYang/-/issues/7)
- **Status:** 🟢 **Ready**

### Issue #6 - Feature: User Location Persistence with Expiry (Retention Policy)
- **GitHub:** [#6](https://gitlab.com/oatricedev/FonMaYang/-/issues/6)
    - ✅ **Done** (0.4.0)

### Issue #5 - Integrate Notification Services for Line OA
- **GitHub:** [#5](https://gitlab.com/oatricedev/FonMaYang/-/issues/5)
- **Status:** 🟢 **Ready**

### Issue #4 - Implement Background Task Scheduler for automated polling
- **GitHub:** [#4](https://gitlab.com/oatricedev/FonMaYang/-/issues/4)
    - ✅ **Done** (0.5.0)

### Issue #3 - Integrate Notification Services (Line OA / Telegram)
- **GitHub:** [#3](https://gitlab.com/oatricedev/FonMaYang/-/issues/3)
    - ✅ **Done** (0.3.0)

### Issue #2 - Implement FastAPI On-demand Routers for RainNowcast
- **GitHub:** [#2](https://gitlab.com/oatricedev/FonMaYang/-/issues/2)
    - ✅ **Done** (0.2.0)

### Issue #1 - Implement Weather Services MVP (Base, RainViewer, Rainbow) with TDD
- **GitHub:** [#1](https://gitlab.com/oatricedev/FonMaYang/-/issues/1)
- **Status:** 🟢 **Ready**

