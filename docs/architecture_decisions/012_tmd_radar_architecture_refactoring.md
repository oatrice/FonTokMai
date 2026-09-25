# 012 - TMD Radar Architecture Refactoring and Domain Isolation

**Date:** 2026-09-24  
**Status:** Accepted  

## Context

The `TMDRadarProcessor` had evolved into a "God Object" over time. It was responsible for:
1. Fetching configurations and stations.
2. Managing cache and data synchronization.
3. Running mathematical algorithms (pixel mapping, optical flow).
4. Generating image visual outputs (OpenCV, PIL drawing, text rendering).
5. Returning raw unstructured dictionaries back to the core application logic.

This violated the Single Responsibility Principle (SRP) and made the codebase difficult to test, maintain, and scale. Furthermore, returning raw dictionaries without strict types caused cascading errors whenever the internal structures changed, making the boundaries between the `TMDNowcastAdapter` and `WeatherManager` fragile.

## Decisions

We executed a comprehensive 4-phase architectural refactoring plan based on an external architecture review:

1. **Phase 1: Foundation (Radar Stations & Config Registry)**
   - Extracted configuration management into a `TMDRadarRegistry` class.
   - Centralized station metadata (bbox, static crop sizes) in the registry, replacing hardcoded globals.

2. **Phase 2: Data Seam (Global Radar Cache)**
   - Extracted all Firestore and database logic from the processor into a dedicated `TMDRadarCacheManager`.
   - Made the CacheManager responsible for storing and retrieving live radar frames.

3. **Phase 3: Domain Isolation (NowcastPort & TMDNowcastAdapter)**
   - Introduced `NowcastPort` as the primary interface for any radar service.
   - Refactored the `TMDRadarProcessor` inside a `TMDNowcastAdapter` implementing the `NowcastPort`, ensuring the core app (`WeatherManager`) only speaks to the interface, not the concrete TMD implementation.

4. **Phase 4: RadarRenderer and RadarPredictionEntity**
   - Created the `RadarPredictionEntity` and `RainPrediction` Pydantic models to replace unstructured dictionaries.
   - Extracted all OpenCV/PIL image drawing logic (e.g., `generate_radar_tracking_image`, `generate_timeline_image`) into a `DefaultRadarRenderer` implementing a `RadarRenderer` protocol.
   - The processor now focuses solely on calculating math and tracking data, and delegates to the renderer for image generation.

## Consequences

### Positive
- **Clear Separation of Concerns:** Core math logic, data access, and presentation layers are now strictly isolated.
- **Type Safety:** The boundary between the radar logic and `WeatherManager` is protected by `RadarPredictionEntity`, providing IDE completion and strict validation.
- **Testability:** Mocking and testing individual pieces (e.g., the renderer or the processor math) is significantly easier without side effects from the other responsibilities.

### Negative
- **More files to navigate:** The logic is spread across multiple files (`adapter.py`, `processor.py`, `renderer_impl.py`, `cache_manager.py`, `entities.py`).
- **Data Conversion Overhead:** There is a minor computational overhead to serialize and parse Pydantic models between the layers.

