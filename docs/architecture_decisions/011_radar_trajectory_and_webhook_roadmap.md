# Architecture & Multi-Issue MR Roadmap: Radar Trajectory, Webhook Architecture & Interactive Maps

## 1. Executive Summary & Jobs To Be Done (JTBD)
- **User Job:** "When I check the weather or get alerted via Telegram/LINE, I want accurate rain trajectory predictions without false alerts or floating lines, so I can plan my travel with complete confidence."
- **Admin/Operator Job:** "When I monitor radar status across Thailand, I want a real-time visual map and unified webhook architecture, so I can diagnose station outages and maintain reliable multi-channel messaging easily."
- **Engineering Job:** "When validating radar algorithms, I want deterministic, hermetic test fixtures and modular code under 500 LOC per MR, so that CI pipelines are lightning fast, flake-free, and safe to deploy."

---

## 2. C4 Container Architecture Diagram

```mermaid
C4Container
    title Container Diagram for FonMaYang Radar & Notification Platform

    Person(user, "End User", "Receives accurate rain alerts and requests live radar summaries via Telegram/LINE")
    Person(admin, "Admin / Operator", "Monitors station health and inspects radar calibration via Web Portal")

    System_Boundary(fonmayang, "FonMaYang Platform") {
        Container(webApp, "Web Frontend App", "Next.js 14, TailwindCSS, Leaflet/Mapbox", "Interactive weather maps, cluster hover trajectories, and admin portal (/admin/radar)")
        Container(apiServer, "API & Webhook Engine", "FastAPI, Python 3.13, OpenCV, Pillow", "Receives webhooks, performs Semi-Lagrangian nowcasting, renders visual tracking/multiframe composites")
        Container(cloudTasks, "Asynchronous Queue", "GCP Cloud Tasks", "Offloads heavy radar frame polling, image processing, and notification dispatch")
        ContainerDb(neonDb, "Relational Database", "Neon Serverless PostgreSQL", "Stores radar stations, user locations, system configs, and operational metrics")
        ContainerDb(firestoreStorage, "Object Storage & State", "Firebase Storage & Firestore", "Stores raw radar GIF frames, tracking composites, and distributed locks")
    }

    System_Ext(tmdRadar, "Thai Meteorological Dept (TMD)", "Provides nationwide radar GIF/JPG frames")
    System_Ext(telegramApi, "Telegram Bot API", "Delivers interactive alerts, /multiframe & 2-subimage composites")
    System_Ext(lineApi, "LINE Messaging API", "Delivers rich Flex Messages and radar photos")

    Rel(user, telegramApi, "Interacts with", "HTTPS")
    Rel(user, lineApi, "Interacts with", "HTTPS")
    Rel(user, webApp, "Views live maps & runway on", "HTTPS")
    Rel(admin, webApp, "Monitors radar health on /admin/radar", "HTTPS")

    Rel(telegramApi, apiServer, "Sends webhooks to", "HTTPS/JSON")
    Rel(lineApi, apiServer, "Sends webhooks to", "HTTPS/JSON")
    Rel(webApp, apiServer, "Fetches stations & forecast from", "HTTPS/JSON")

    Rel(apiServer, cloudTasks, "Enqueues heavy radar processing to", "gRPC/HTTP")
    Rel(cloudTasks, apiServer, "Dispatches async worker task to", "HTTPS/JSON")

    Rel(apiServer, tmdRadar, "Polls radar frames from", "HTTP/GIF")
    Rel(apiServer, neonDb, "Reads/Writes stations & configs to", "asyncpg/SQL")
    Rel(apiServer, firestoreStorage, "Caches radar frames to", "GCS/REST")
    Rel(apiServer, telegramApi, "Dispatches photo/text responses to", "HTTPS/JSON")
    Rel(apiServer, lineApi, "Dispatches Flex/Image responses to", "HTTPS/JSON")
```

---

## 3. Domain-Driven Design (DDD) & Bounded Contexts

```mermaid
graph TD
    subgraph Core_Radar_Domain ["Core Radar & Nowcasting Domain (MR1)"]
        TrackingEngine["Radar Tracking & Extrapolation Engine"]
        TrajectoryValidator["Cloud-Trajectory Connectivity Validator"]
        DeterministicClock["Anchor Time & Fixture Clock"]
        VisualRenderer["2-Subimage & Multi-Frame Composite Renderer"]
    end

    subgraph Channel_Presentation_Domain ["Channel Presentation & Webhook Domain (MR2)"]
        SharedMessageProcessor["Shared Forecast Text & Alert Builder"]
        MediaExtractor["Unified Media Stream & Storage Extractor"]
        TelegramAdapter["Telegram Direct-Byte Stream Adapter"]
        LineAdapter["LINE GCS Public URL Adapter"]
    end

    subgraph Visualization_Domain ["Interactive Web & Admin Domain (MR3)"]
        AdminStationStatus["Real-time Station Health & Coverage Page (/admin/radar)"]
        ClusterHoverPreview["Leaflet/Mapbox Cloud Cluster Hover Trajectory"]
    end

    Core_Radar_Domain -->|Nowcast & Rendered Composites| Channel_Presentation_Domain
    Core_Radar_Domain -->|Station Metadata & Active Clusters| Visualization_Domain
```

---

## 4. Multi-Issue MR Roadmap (< 500 LOC per MR)

### 🚀 MR 1: Radar Trajectory Precision & Bot Multi-Frame Presentation
- **Issues Resolved:** `#268`, `#263`, `#183`
- **Estimated Scope:** ~320 LOC
- **Bounded Context:** Core Radar Nowcasting & Telegram Command Router
- **Key Deliverables:**
  1. **Suppress False Trajectory & Alert (#268):** Validate that predicted cloud points intersect with an actively detected cloud cluster before rendering blue trajectory lines or emitting rain status text.
  2. **2-Subimage Composite & `/multiframe` (#263):** Replace 4-panel tracking image with clean 2-subimage layout (`Raw image with grid` vs `Final prediction overlay`) and add standalone `/multiframe` command.
  3. **Deterministic Fixture Tests (#183):** Decouple `datetime.now()` wall-clock from `extrapolate_rain_at_pixel` and `weather_manager.py` using explicit anchor timestamps.

---

### 📦 MR 2: Unified Telegram & LINE Webhook Architecture & Wind Ghosting
- **Issues Resolved:** `#185`, `#70`
- **Estimated Scope:** ~380 LOC
- **Bounded Context:** Channel Presentation & Media Adaptation
- **Key Deliverables:**
  1. **Shared Message & Media Processor (#185):** Centralize forecast text generation and media extraction in `webhook_utils.py` for both Telegram and LINE.
  2. **Historical Wind Vector Ghosting (#70):** Overlay fading historical wind vector arrows and OpenCV timestamp burning onto cropped radar frames.

---

### 🗺️ MR 3: Web App Radar Hover Trajectory & Admin Status Portal
- **Issues Resolved:** `#270`, `#188`
- **Estimated Scope:** ~420 LOC
- **Bounded Context:** Web Application Frontend & Admin Monitoring
- **Key Deliverables:**
  1. **Admin Station Status Page (#270):** Interactive map on `/admin/radar` showing online/delayed/offline station status across Thailand.
  2. **Cloud Cluster Hover Preview (#188):** Interactive hover state on web maps displaying past trajectory motion vectors of individual clouds.
