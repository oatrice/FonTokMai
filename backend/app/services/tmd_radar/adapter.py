from typing import Dict, Any, Optional, Union
import logging
import asyncio
import time
import json
import re
import math
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import numpy as np
import cv2

from app.services.tmd_radar.nowcast_port import NowcastPort
from app.services.tmd_radar.cache_manager import radar_cache
from app.services.tmd_radar_processor import TMDRadarProcessor
from app.services.weather_manager import _resolve_radar_overlay_utc, log_growth_decay_telemetry
from app.core.dev_settings import get_dev_settings

logger = logging.getLogger(__name__)

class TMDNowcastAdapter(NowcastPort):
    def __init__(self, weather_manager):
        self.weather_manager = weather_manager

    async def predict(
        self, lat: float, lng: float, force_station: Optional[str] = None,
        mock_state: Optional[str] = None, location_name: Optional[str] = None,
        chat_id: Optional[Union[str, int]] = None,
        message_id_to_edit: Optional[Union[str, int]] = None,
        show_labels: bool = True
    ) -> dict:
    
        """
        Wrapper for TMD Radar predictions using Optical Flow Nowcasting.
        Uses dot-product approach vector filter to find approaching cloud clusters,
        then ranks by ETA and generates a smart summary with growth/decay rates.
        """
        
        from app.services.tmd_radar_registry import radar_registry
        from app.database import AsyncSessionLocal
        
        # Fetch stations dynamically from Neon DB (or registry cache)
        stations_map = {}
        try:
            async with AsyncSessionLocal() as session:
                stations_map = await radar_registry.get_all_stations(session)
        except Exception as _e:
            logger.warning(f"Failed to fetch dynamic radar stations, falling back to static config: {_e}")
            from app.services.tmd_radar_config import STATIONS
            stations_map = STATIONS
    
        if force_station:
            stations_to_check = [force_station]
        else:
            def get_dist(code):
                conf = stations_map.get(code)
                if not conf: return float('inf')
                import math
                return math.hypot(lat - conf.center_lat, lng - conf.center_lng)
                
            # Filter stations to only those whose coverage bounding box actually covers (lat, lng)
            covering_stations = []
            for code in stations_map.keys():
                conf = stations_map.get(code)
                if conf:
                    processor = TMDRadarProcessor(code, config=conf)
                    px, py = processor.latlng_to_pixel(lat, lng, is_loop=False)
                    if px is not None and py is not None:
                        covering_stations.append(code)
            
            # If covering stations exist, only check those sorted by distance; otherwise check all sorted by distance
            target_stations = covering_stations if covering_stations else list(stations_map.keys())
            stations_to_check = sorted(target_stations, key=get_dist)
    
        primary_station = stations_to_check[0] if stations_to_check else None
    
        for station_code in stations_to_check:
            try:
                st_conf = stations_map.get(station_code)
                processor = TMDRadarProcessor(station_code, config=st_conf)
                px, py = processor.latlng_to_pixel(lat, lng, is_loop=False)
                if px is None or py is None:
                    continue
    
                async def _status_callback(msg_text: str):
                    if chat_id and message_id_to_edit:
                        try:
                            from app.services import telegram
                            await telegram.edit_telegram_message(int(chat_id), int(message_id_to_edit), msg_text)
                        except Exception as _t_err:
                            logger.warning(f"Failed to update retry status on Telegram: {_t_err}")
    
                # Use module-level cache and lock to prevent cache stampede
                
                    
                lock = radar_cache.get_lock(station_code)
                
                async with lock:
                    cached_data = radar_cache.get(station_code)
                    
                    is_fresh = False
                    if cached_data and (time.time() - cached_data.cache_timestamp) < 600:
                        frame_timestamps = cached_data.frame_timestamps.copy()
                        if frame_timestamps:
                            age = int(time.time() - frame_timestamps[-1])
                            if age < 1200:
                                is_fresh = True
                        else:
                            is_fresh = True
    
                    if is_fresh:
                        frames, last_modified_dt, flow = cached_data.frames, cached_data.last_modified_dt, cached_data.flow
                        frame_source = cached_data.frame_source
                        data_gap_minutes = cached_data.data_gap_minutes
                        frame_timestamps = cached_data.frame_timestamps.copy()
                        frame_urls = cached_data.frame_urls.copy()
                        age_s = int(time.time() - cached_data.cache_timestamp)
                        logger.info(
                            f"[{station_code}] 📦 IN-MEMORY cache HIT — "
                            f"{len(frames)} frames, source={frame_source}, age={age_s}s"
                        )
                    else:
                        cached_data = await self.weather_manager.load_persistent_cache_to_memory(station_code, processor)
                        
                        persistent_stale = True
                        if cached_data:
                            frame_timestamps = cached_data.frame_timestamps.copy()
                            if frame_timestamps:
                                age = int(time.time() - frame_timestamps[-1])
                                if age < 1200:
                                    persistent_stale = False
                                    
                        if persistent_stale:
                            logger.info(f"[{station_code}] Persistent cache is stale or missing. Triggering live radar cache update...")
                            try:
                                await processor.update_radar_cache(force=True, status_callback=_status_callback)
                            except Exception as _e:
                                logger.error(f"[{station_code}] Live cache update failed: {_e}")
                            cached_data = await self.weather_manager.load_persistent_cache_to_memory(station_code, processor)
                            
                        if cached_data:
                            frames, last_modified_dt, flow = cached_data.frames, cached_data.last_modified_dt, cached_data.flow
                            frame_source = cached_data.frame_source
                            data_gap_minutes = cached_data.data_gap_minutes
                            frame_timestamps = cached_data.frame_timestamps.copy()
                            frame_urls = cached_data.frame_urls.copy()
                        else:
                            frames = []
                            last_modified_dt = None
                            flow = None
                            frame_source = "static_cache"
                            frame_timestamps = []
                            data_gap_minutes = 15.0
                            frame_urls = []
                        if not frames or len(frames) < 2:
                            fresh_frames, fresh_dt, fresh_loop_bytes = await processor.fetch_loop_gif_and_extract_frames(status_callback=_status_callback)
                            if len(fresh_frames) >= 2:
                                frames = fresh_frames[-6:]
                                target_shape = frames[-1].shape[:2]
                                for i in range(len(frames)-1):
                                    if frames[i].shape[:2] != target_shape:
                                        frames[i] = cv2.resize(frames[i], (target_shape[1], target_shape[0]), interpolation=cv2.INTER_NEAREST)
                                last_modified_dt = fresh_dt or datetime.now(timezone.utc)
                                if fresh_dt:
                                    latest_ts = int(fresh_dt.timestamp())
                                    frame_timestamps = [
                                        latest_ts - (len(frames) - 1 - i) * 900
                                        for i in range(len(frames))
                                    ]
                                else:
                                    frame_timestamps = []
                                if get_dev_settings().flow_mode == "average":
                                    flow = processor.calculate_average_optical_flow(frames)
                                else:
                                    flow = processor.calculate_optical_flow(frames)
                                data_gap_minutes = 15.0 # Loop GIFs are assumed to be exactly 15m apart
                                frame_source = "loop_gif"
                                logger.warning(
                                    f"[{station_code}] 🌀 LIVE loop GIF fallback — "
                                    f"{len(frames)} frames fetched direct from TMD (Firestore cache was empty/stale)"
                                )
                                # Also persist to Firestore so next call after in-memory expiry
                                # uses Firestore instead of re-fetching loop GIF again.
                                saved_frames = []
                                try:
                                    # Crop parameters for loop frames
                                    lcy = processor.config.loop_crop_y
                                    lcx = processor.config.loop_crop_x
                                    lch = processor.config.loop_crop_height
                                    lcw = processor.config.loop_crop_width
                                    for f_img, f_ts in zip(frames, frame_timestamps):
                                        # Max 800 normalize
                                        h, w = f_img.shape[:2]
                                        if h > 800 or w > 800:
                                            scale = 800.0 / float(max(h, w))
                                            f_norm = cv2.resize(f_img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
                                        else:
                                            f_norm = f_img
    
                                        if (lcy + lch <= f_norm.shape[0]) and (lcx + lcw <= f_norm.shape[1]):
                                            f_save = f_norm[lcy:lcy + lch, lcx:lcx + lcw]
                                        else:
                                            f_save = f_norm
    
                                        is_ok, buf = cv2.imencode(".png", cv2.cvtColor(f_save, cv2.COLOR_RGB2BGR))
                                        if is_ok:
                                            f_url = await processor.save_polled_frame(buf.tobytes())
                                            saved_frames.append({"url": f_url, "timestamp": f_ts})
    
                                    if saved_frames:
                                        async with get_repo_context() as _repo:
                                            await _repo.set_latest_radar_cache(
                                                station_code=station_code,
                                                frames=saved_frames,
                                            )
                                        logger.info(
                                            f"[{station_code}] 🌀 GIF fallback: persisted "
                                            f"{len(saved_frames)} cropped frames to Firestore"
                                        )
                                except Exception as _e:
                                    logger.warning(f"[{station_code}] 🌀 GIF fallback: Firestore persist failed: {_e}")
                                # Collect frame URLs from saved frames for reproducibility
                                frame_urls = [sf["url"] for sf in saved_frames] if saved_frames else []
                                radar_cache.set(station_code, frames, last_modified_dt, flow, frame_source, data_gap_minutes, frame_timestamps, frame_urls)
                            else:
                                continue
    
    
                if not frames or len(frames) < 2:
                    continue
    
                curr_frame = frames[-1].copy()
                prev_frame = frames[-2].copy()
    
                now_utc = await _resolve_radar_overlay_utc(
                    frames[-1],
                    last_modified_dt,
                    frame_timestamps,
                    processor=processor,
                    frame_source=frame_source,
                )
                logger.info(f"DEBUG_NOW_UTC: station={station_code}, now_utc={now_utc}, frame_timestamps={frame_timestamps}")
    
                # Determine if frames came from the loop GIF (vs static image).
                # We rely on frame_source which is set reliably during loading.
                # The old shape[1] <= 1000 heuristic was unreliable: raw GIF
                # frames are 1920×1600 and were mis-classified as static.
                use_loop_mapping = (frame_source == "loop_gif")
    
                # ── Normalize legacy uncropped loop frames ──────────────────────────
                # Frames cached in GCS before the crop-before-save fix may still be
                # full-canvas (e.g. 800×800) instead of the expected loop crop size
                # (e.g. 720×720).  An uncropped frame causes latlng_to_pixel to enter
                # the legacy-scaling branch where config_canvas_h (= crop_y + crop_h
                # = 760 for kkn240) ≠ actual_h (800), leading to scale_y ≈ 1.053
                # and a ~25 px y-shift in the computed pin position.
                # We detect this by comparing the actual frame dimensions to the
                # configured crop size and crop on-the-fly if needed.
                if use_loop_mapping and curr_frame is not None:
                    _cfg = processor.config
                    _lcx, _lcy = _cfg.loop_crop_x, _cfg.loop_crop_y
                    _lch, _lcw = _cfg.loop_crop_height, _cfg.loop_crop_width
                    _fh, _fw = curr_frame.shape[:2]
                    _needs_crop = (
                        (_fh > _lch or _fw > _lcw)
                        and (_lcy + _lch <= _fh)
                        and (_lcx + _lcw <= _fw)
                    )
                    if _needs_crop:
                        logger.info(
                            f"[{station_code}] 🔧 On-the-fly loop frame crop: "
                            f"{_fw}×{_fh} → {_lcw}×{_lch} "
                            f"(legacy GCS frame pre-dates crop-before-save fix)"
                        )
                        frames = [
                            f[_lcy:_lcy + _lch, _lcx:_lcx + _lcw]
                            for f in frames
                        ]
                        curr_frame = frames[-1].copy()
                        prev_frame = frames[-2].copy()
    
                actual_frame_shape = curr_frame.shape[:2] if curr_frame is not None else None
                user_px, user_py = processor.latlng_to_pixel(
                    lat, lng,
                    is_loop=use_loop_mapping,
                    frame_shape=actual_frame_shape,
                )
                px, py = user_px, user_py
    
                if chat_id:
                    try:
                        WeatherManager.LAST_USED_STATION[int(chat_id)] = station_code
                    except Exception:
                        pass
    
                import logging
                logging.info(f"DEBUG_LOCATION: lat={lat}, lng={lng} -> user_px={user_px}, user_py={user_py} (station: {station_code}, is_loop={use_loop_mapping})")
                if user_px is None or user_py is None:
                    continue
    
                # Log frame identity for reproducibility (so offline test can match exact frames)
                logger.info(
                    f"[FRAME_ID] station={station_code}, source={frame_source}, "
                    f"n_frames={len(frames)} (last_ts={frame_timestamps[-1] if frame_timestamps else '?'}), "
                    f"timestamps={frame_timestamps}, shape={frames[-1].shape[:2]}, "
                    f"urls={frame_urls}"
                )
    
                # Find all cloud clusters approaching the user (using dev-configurable thresholds)
                _cfg = get_dev_settings()
                clouds = processor.find_approaching_clouds(
                    curr_frame, prev_frame, flow, user_px, user_py,
                    search_radius=_cfg.search_radius,
                    min_dbz=_cfg.min_dbz,
                    cluster_dist=10,
                    hit_radius=_cfg.hit_radius,
                    cluster_min=_cfg.cluster_min,
                    dot_threshold=_cfg.dot_threshold,
                )
                # Also collect ALL rain clusters (any direction) for the always-visible overlay
                all_rain_clusters = await asyncio.to_thread(
                    processor.get_all_rain_clusters,
                    curr_frame, flow, user_px, user_py,
                    scan_radius=None,
                    min_dbz=_cfg.min_dbz,
                    cluster_dist=6,
                    min_size=5,
                )
                
                if all_rain_clusters:
                    min_amb_dbz = _cfg.min_ambient_dbz
                    min_amb_size = _cfg.min_ambient_size
                    filtered_clusters = []
                    for c in all_rain_clusters:
                        if len(c.get("pixels", [])) < 5:
                            filtered_clusters.append(c)
                            continue
                        dbz = c.get("dbz_now", 0)
                        size = len(c.get("pixels", []))
                        if dbz >= min_amb_dbz and size >= min_amb_size:
                            filtered_clusters.append(c)
                        else:
                            logger.info(
                                f"[FILTER] Ambient cluster filtered out: centroid=({c.get('cx'):.1f}, {c.get('cy'):.1f}), "
                                f"dbz={dbz:.1f}, size={size}px (thresholds: dbz>={min_amb_dbz}, size>={min_amb_size})"
                            )
                    all_rain_clusters = filtered_clusters
    
                if all_rain_clusters:
                    # Sort by dBZ descending first, then distance ascending so red/heavy rain clusters get labels A, B...
                    all_rain_clusters.sort(key=lambda c: (-c.get("predicted_dbz", c.get("dbz_now", 20)), c.get("dist", 9999)))
                    for i, c in enumerate(all_rain_clusters):
                        # Only label the first 26 clusters (A-Z). Clusters beyond that get None
                        # to avoid all of them collapsing to 'Z'.
                        c["label"] = chr(ord('A') + i) if i < 26 else None
                        
                # Match labels from all_rain_clusters to clouds
                if all_rain_clusters and clouds:
                    unique_clouds = {}
                    for appr_c in clouds:
                        matched_label = "?"
                        min_d = 9999
                        matched_amb = None
                        for amb_c in all_rain_clusters:
                            d = math.hypot(appr_c["cx"] - amb_c["cx"], appr_c["cy"] - amb_c["cy"])
                            if d < 150 and d < min_d:
                                min_d = d
                                matched_label = amb_c.get("label", "?")
                                matched_amb = amb_c
                                
                        appr_c["label"] = matched_label
                        if matched_amb:
                            appr_c["cx"] = matched_amb["cx"]
                            appr_c["cy"] = matched_amb["cy"]
                            if "peak_cx" in matched_amb:
                                appr_c["peak_cx"] = matched_amb["peak_cx"]
                            if "peak_cy" in matched_amb:
                                appr_c["peak_cy"] = matched_amb["peak_cy"]
                            if "pixels" in matched_amb:
                                appr_c["pixels"] = matched_amb["pixels"]
                                
                        # Deduplicate: keep the one with smaller absolute eta (closer to impact or current)
                        label = appr_c["label"]
                        if label not in unique_clouds:
                            unique_clouds[label] = appr_c
                        else:
                            existing = unique_clouds[label]
                            if abs(appr_c.get("eta_min", 9999)) < abs(existing.get("eta_min", 9999)):
                                unique_clouds[label] = appr_c
                    clouds = list(unique_clouds.values())
    
                tracking_mode = "auto"
                locked_target_id = None
                locked_target_cx = None
                locked_target_cy = None
                matched_target = None
                
                if chat_id:
                    async with get_repo_context() as repo:
                        loc_record = await repo.get_location(chat_id, location_name) if location_name else None
                        if not loc_record:
                            loc_record = await repo.get_location(chat_id, "default")
                        if loc_record:
                            tracking_mode = getattr(loc_record, "tracking_mode", "auto")
                            locked_target_id = getattr(loc_record, "locked_target_id", None)
                            locked_target_cx = getattr(loc_record, "locked_target_cx", None)
                            locked_target_cy = getattr(loc_record, "locked_target_cy", None)
                            logger.info(f"[DEBUG_LOCK] DB read: loc_name={getattr(loc_record, 'name', '?')}, tracking_mode={tracking_mode}, locked_target_id={locked_target_id}, cx={locked_target_cx}, cy={locked_target_cy}")
                            
                if tracking_mode == "manual" and locked_target_cx is not None and locked_target_cy is not None:
                    min_dist = 9999
                    
                    is_grid_cell = False
                    cell_center_x, cell_center_y = None, None
                    if locked_target_id:
                        import re
                        m = re.match(r"^([a-hA-H])[-_]?([1-8])$", locked_target_id)
                        if m:
                            is_grid_cell = True
                            col_char = m.group(1).upper()
                            row_char = m.group(2)
                            grid_col_idx = ord(col_char) - ord('A')
                            grid_row_idx = int(row_char) - 1
                            
                            crop_r = 120
                            crop_x1 = max(0, user_px - crop_r)
                            crop_y1 = max(0, user_py - crop_r)
                            frame_w = curr_frame.shape[1]
                            frame_h = curr_frame.shape[0]
                            crop_x2 = min(frame_w, user_px + crop_r)
                            crop_y2 = min(frame_h, user_py + crop_r)
                            cell_w = (crop_x2 - crop_x1) / 8.0
                            cell_h = (crop_y2 - crop_y1) / 8.0
                            cell_center_x = int(crop_x1 + (grid_col_idx + 0.5) * cell_w)
                            cell_center_y = int(crop_y1 + (grid_row_idx + 0.5) * cell_h)
                            
                            cell_x_min = crop_x1 + grid_col_idx * cell_w - 5.0
                            cell_x_max = crop_x1 + (grid_col_idx + 1) * cell_w + 5.0
                            cell_y_min = crop_y1 + grid_row_idx * cell_h - 5.0
                            cell_y_max = crop_y1 + (grid_row_idx + 1) * cell_h + 5.0
    
                    for cluster in all_rain_clusters:
                        dist = math.hypot(cluster["cx"] - locked_target_cx, cluster["cy"] - locked_target_cy)
                        
                        if is_grid_cell and (cell_x_min <= locked_target_cx <= cell_x_max and cell_y_min <= locked_target_cy <= cell_y_max):
                            if not (cell_x_min <= cluster["cx"] <= cell_x_max and cell_y_min <= cluster["cy"] <= cell_y_max):
                                continue
                                
                        if dist < 120 and dist < min_dist:
                            min_dist = dist
                            matched_target = cluster
    
                    # Fallback: if grid-cell constraint filtered out everything, search
                    # for a cluster that has at least one rain pixel physically inside
                    # the target grid cell. This catches large clusters whose centroid
                    # sits outside the cell but whose body overlaps it.
                    if matched_target is None and is_grid_cell:
                        logger.info(f"[DEBUG_LOCK] Grid-cell search found nothing — checking pixel overlap (locked_cx={locked_target_cx}, locked_cy={locked_target_cy})")
                        for cluster in all_rain_clusters:
                            pixels = cluster.get("pixels", [])
                            for px_coord, py_coord in pixels:
                                if cell_x_min <= px_coord <= cell_x_max and cell_y_min <= py_coord <= cell_y_max:
                                    dist = math.hypot(cluster["cx"] - locked_target_cx, cluster["cy"] - locked_target_cy)
                                    if dist < min_dist:
                                        min_dist = dist
                                        matched_target = cluster
                                    break
    
                    if matched_target:
                        logger.info(f"[DEBUG_LOCK] matched_target FOUND: label={matched_target.get('label')}, cx={matched_target['cx']}, cy={matched_target['cy']}, dist={min_dist:.1f}")
                        # Update DB so future predict_rain calls track from cluster centroid.
                        async with get_repo_context() as repo:
                            await repo.update_tracking_mode(
                                chat_id=chat_id,
                                tracking_mode="manual",
                                locked_target_id=locked_target_id,
                                # Grid-cell locks: preserve the original cell-center pixel in DB
                                # so the lock icon always appears at the named cell, not at the
                                # matched cluster's centroid (which may be outside the crop window).
                                # Label-based locks: follow the cluster as it drifts.
                                locked_target_cx=locked_target_cx if is_grid_cell else matched_target["cx"],
                                locked_target_cy=locked_target_cy if is_grid_cell else matched_target["cy"],
                                name=location_name or "default"
                            )
                        if not is_grid_cell:
                            # For label-based locks: follow the cluster as it moves.
                            locked_target_cx = matched_target["cx"]
                            locked_target_cy = matched_target["cy"]
    
                    else:
                        logger.warning(f"[DEBUG_LOCK] matched_target NOT FOUND: locked_cx={locked_target_cx}, locked_cy={locked_target_cy}, n_clusters={len(all_rain_clusters)}, closest_dist={min_dist:.1f}")
    
                # ── Parametric scenario mock (JSON mock_state) ────────────────────
                if mock_state and mock_state.startswith("{"):
                    try:
                        scenario = json.loads(mock_state)
                        # Override clouds completely with synthetic data
                        # Estimate km_per_pixel from station config
                        lon_diff = processor.config.bbox.lng_max - processor.config.bbox.lng_min
                        width_km = lon_diff * 111.0
                        est_km_per_pixel = width_km / max(1, processor.config.loop_crop_width)
                        clouds = _build_mock_clouds_from_scenario(
                            scenario, user_px, user_py, km_per_pixel=est_km_per_pixel
                        )
                    except Exception as e:
                        logger.warning(f"Failed to parse JSON mock_state scenario: {e}")
    
                # Apply mock overrides
                elif mock_state in ("rain", "storm"):
                    if mock_state == "storm" or not clouds:
                        if mock_state == "storm":
                            clouds = []  # Forcefully clear real clouds to ensure mock storm always shows
                        mock_configs = []
                        if mock_state == "storm":
                            import random
                            intensities = [
                                ((0, 128, 0), 25.0),    # Green exact
                                ((255, 255, 0), 35.0),  # Yellow exact
                                ((255, 128, 0), 45.0),  # Orange exact
                                ((128, 0, 0), 55.0),    # Dark Red exact
                                ((255, 0, 255), 65.0),  # Magenta/Purple exact
                            ]
                            random.shuffle(intensities)
                            bands = [
                                {"color": intensities[0][0], "dbz": intensities[0][1], "base_offset": (-5, 5),   "eta": 0},
                                {"color": intensities[1][0], "dbz": intensities[1][1], "base_offset": (-20, 20), "eta": 5},
                                {"color": intensities[2][0], "dbz": intensities[2][1], "base_offset": (-35, 35), "eta": 10},
                                {"color": intensities[3][0], "dbz": intensities[3][1], "base_offset": (-50, 50), "eta": 15},
                                {"color": intensities[4][0], "dbz": intensities[4][1], "base_offset": (-65, 65), "eta": 20},
                            ]
                        else:
                            # Incoming rain scenario: storm is further away, warning in advance
                            bands = [
                                {"color": (46, 204, 113),  "dbz": 25.0, "base_offset": (-25, 25), "eta": 30},  # Green
                                {"color": (241, 196, 15),  "dbz": 35.0, "base_offset": (-35, 35), "eta": 45},  # Yellow
                            ]
                            
                        for band in bands:
                            bx, by = band["base_offset"]
                            for spread in [-60, -30, 0, 30, 60]:
                                mock_configs.append({
                                    "color": band["color"],
                                    "dbz": band["dbz"],
                                    "offset": (bx + spread, by + spread),
                                    "eta": band["eta"]
                                })
    
                        for mc in mock_configs:
                            cx, cy = user_px + mc["offset"][0], user_py + mc["offset"][1]
                            vx, vy = (5.0, -5.0) if mock_state == "rain" else (3.0, -3.0)  # Move towards NE
                            clouds.append({
                                "cx": cx, "cy": cy,
                                "vx": vx, "vy": vy,
                                "dbz_now": mc["dbz"], "dbz_prev": mc["dbz"] - 2.0,
                                "predicted_dbz": mc["dbz"],
                                "eta_min": mc["eta"],
                                "growth_rate": 0.05,
                                "dist": max(1, abs(mc["offset"][0]))
                            })
                            
                            if mock_state == "storm":
                                cv2.circle(curr_frame, (cx, cy), 22, mc["color"], -1)
                    else:
                        for c in clouds:
                            c["dbz_now"]       = max(c["dbz_now"], 40.0)
                            c["predicted_dbz"] = max(c["predicted_dbz"], 40.0)
                elif mock_state == "clear":
                    clouds = []
    
                current_utc = datetime.now(timezone.utc)
                time_offset_min = (current_utc - now_utc).total_seconds() / 60.0
                # If the data age is more than 24 hours, it is likely mock or historical data for testing.
                # Reset time_offset_min to 0.0 so that timelines and ETAs are calculated relative to the latest frame.
                if time_offset_min > 1440.0:
                    time_offset_min = 0.0
                data_age_minutes = time_offset_min
                
                confidence_score = 1.0
                # Using data_gap_minutes which was computed earlier (defaults to 15.0 if not bound)
                try:
                    gap_min = data_gap_minutes
                except NameError:
                    gap_min = 15.0
                    
                if gap_min > 20 or data_age_minutes > 30:
                    confidence_score = 0.5
    
    
                def dbz_to_intensity(d: float) -> str:
                    if d >= 55: return "ฝนตกหนักมาก"
                    if d >= 35: return "ฝนตกหนัก"
                    if d >= 20: return "ฝนตกปานกลาง"
                    if d > 0:   return "ฝนตกเล็กน้อย"
                    return "ไม่มีฝน"
    
                predictions = []
                max_dbz = 0.0
                current_dbz = processor.get_dbz_at_pixel(curr_frame, px, py)
                
                fallback_vx, fallback_vy = 0.0, 0.0
                manual_rate = None
                
                if tracking_mode == "manual" and matched_target:
                    fallback_vx = matched_target.get("vx", 0.0)
                    fallback_vy = matched_target.get("vy", 0.0)
                    manual_rate = matched_target.get("growth_rate", 0.0)
                elif clouds:
                    closest_c = min(clouds, key=lambda c: c.get("dist", 9999))
                    fallback_vx = closest_c.get("vx", 0.0)
                    fallback_vy = closest_c.get("vy", 0.0)
                
                for steps in range(_cfg.prediction_steps):
                    offset_min = steps * 15
                    
                    rate = 0.0
                    if _cfg.decay_enabled:
                        if tracking_mode == "manual" and matched_target:
                            rate = manual_rate if manual_rate is not None else 0.0
                        elif clouds:
                            closest_c = min(clouds, key=lambda c: c.get("dist", 9999))
                            rate = closest_c.get("growth_rate", 0.0)
                        
                    dbz, src_x, src_y = processor.extrapolate_rain_at_pixel(
                        curr_frame, flow, px, py, steps=steps, rate=rate, radius=_cfg.hit_radius,
                        fallback_vx=fallback_vx, fallback_vy=fallback_vy
                    )
                    
                    if tracking_mode == "manual":
                        if matched_target:
                            # Check if the rain found at src_x,src_y belongs to the locked
                            # cluster. Use pixel-set proximity (50px to nearest cluster pixel)
                            # rather than centroid proximity so that large/elongated clusters
                            # whose body extends toward home are not falsely zeroed out.
                            pixels = matched_target.get("pixels", [])
                            if pixels:
                                min_px_dist = min(
                                    math.hypot(px_c - src_x, py_c - src_y)
                                    for px_c, py_c in pixels
                                )
                                if min_px_dist > 50.0:
                                    dbz = 0.0
                            else:
                                # No pixel list — fall back to centroid check with wider threshold
                                if math.hypot(src_x - matched_target["cx"], src_y - matched_target["cy"]) > 80.0:
                                    dbz = 0.0
                        else:
                            dbz = 0.0
                    
                    cluster_label = None
                    if dbz >= 10.0 and all_rain_clusters:
                        min_dist = 9999
                        # Primary pass: within bbox + 20px margin
                        for c in all_rain_clusters:
                            if c.get("label") is None:
                                continue
                            dx = max(c.get("xmin", c["cx"]) - src_x, 0, src_x - c.get("xmax", c["cx"]))
                            dy = max(c.get("ymin", c["cy"]) - src_y, 0, src_y - c.get("ymax", c["cy"]))
                            d = math.hypot(dx, dy)
                            if d <= 20 and d < min_dist:
                                min_dist = d
                                cluster_label = c.get("label")
                        # Fallback pass: use nearest labelled cluster centroid within 80px
                        # (future prediction steps shift src away from the cluster bbox)
                        if cluster_label is None:
                            for c in all_rain_clusters:
                                if c.get("label") is None:
                                    continue
                                d = math.hypot(c["cx"] - src_x, c["cy"] - src_y)
                                if d <= 80 and d < min_dist:
                                    min_dist = d
                                    cluster_label = c.get("label")
                                    
                    if mock_state == "rain":
                        dbz = max(dbz, 40.0)
                    elif mock_state == "clear":
                        dbz = 0.0
                    elif mock_state and mock_state.startswith("{"):
                        try:
                            scenario = json.loads(mock_state)
                            if scenario.get("no_rain") or scenario.get("clear"):
                                dbz = 0.0
                            else:
                                mock_dbz = float(scenario.get("dbz", 35.0))
                                if "rain_in" in scenario:
                                    rain_in = float(scenario["rain_in"])
                                    if offset_min >= rain_in:
                                        dbz = max(dbz, mock_dbz)
                                elif "rain_stopping" in scenario:
                                    rain_stopping = float(scenario["rain_stopping"])
                                    if offset_min < rain_stopping:
                                        dbz = max(dbz, mock_dbz)
                                else:
                                    # Default fallback to mock dbz if not specified
                                    dbz = max(dbz, mock_dbz)
                        except Exception:
                            pass
                        
                    if dbz > max_dbz:
                        max_dbz = dbz
                    
                    pred_time  = now_utc + timedelta(minutes=steps * 15)
                    z_value    = 10 ** (dbz / 10.0)
                    rain_mmhr  = (z_value / 200.0) ** (1.0 / 1.6) if dbz > 0 else 0.0
                    predictions.append({
                        "time":        pred_time.isoformat().replace("+00:00", "Z"),
                        "time_offset": steps * 15,
                        "intensity":   dbz_to_intensity(dbz),
                        "dbz":         float(dbz),
                        "rain":        float(rain_mmhr),
                        "cluster":     cluster_label,
                        "src_x":       int(src_x),
                        "src_y":       int(src_y)
                    })
                    
                    if get_dev_settings().verbose:
                        logger.info(f"[VERBOSE] Step {steps} (+{offset_min}m): dbz={dbz:.1f} src=({src_x},{src_y}) cluster={cluster_label}")
    
                current_dbz = predictions[0]["dbz"]
                intensity   = predictions[0]["intensity"]
                v_close_kmh = None
                v_actual_kmh = None
                v_avg_kmh = None
                if tracking_mode == "manual" and matched_target:
                    cx, cy = matched_target["cx"], matched_target["cy"]
                    dx = px - cx
                    dy = py - cy
                    dist = math.hypot(dx, dy)
                    
                    # Find maximum wind speed from all pixels in the cluster
                    max_v_mag = 0.0
                    peak_vx = fallback_vx
                    peak_vy = fallback_vy
                    if "pixels" in matched_target and matched_target["pixels"]:
                        for px_coord in matched_target["pixels"]:
                            x_p, y_p = px_coord
                            if 0 <= x_p < flow.shape[1] and 0 <= y_p < flow.shape[0]:
                                fx = float(flow[y_p, x_p, 0])
                                fy = float(flow[y_p, x_p, 1])
                                v_mag = math.hypot(fx, fy)
                                if v_mag > max_v_mag:
                                    max_v_mag = v_mag
                                    peak_vx = fx
                                    peak_vy = fy
                    else:
                        peak_vx = float(flow[cy, cx, 0]) if (0 <= cx < flow.shape[1] and 0 <= cy < flow.shape[0]) else fallback_vx
                        peak_vy = float(flow[cy, cx, 1]) if (0 <= cx < flow.shape[1] and 0 <= cy < flow.shape[0]) else fallback_vy
                    
                    if dist > 0:
                        v_close = (peak_vx * dx + peak_vy * dy) / dist
                    else:
                        v_close = 0.0
                    lon_diff = processor.config.bbox.lng_max - processor.config.bbox.lng_min
                    width_km = lon_diff * 111.0
                    km_per_pixel = width_km / 800.0
                    v_close_kmh = v_close * km_per_pixel * 4.0
                    v_avg_kmh = processor.get_wind_speed_kmh_from_vector(fallback_vx, fallback_vy)
                    v_actual_kmh = processor.get_wind_speed_kmh_from_vector(peak_vx, peak_vy)
    
                summary_line = processor.render_rain_summary(
                    predictions=predictions,
                    time_offset_min=time_offset_min,
                    confidence_score=confidence_score,
                    approaching_clouds=clouds,
                    locked_target_id=locked_target_id if tracking_mode == "manual" else None,
                    all_rain_clusters=all_rain_clusters,
                    v_close_kmh=v_close_kmh,
                    v_actual_kmh=v_actual_kmh,
                    v_avg_kmh=v_avg_kmh
                )
                # Sync cluster ETA with accurate pixel-level predictions
                if clouds:
                    for c in clouds:
                        c_lbl = c.get("label")
                        if not c_lbl: continue
                        for p in predictions:
                            if p["cluster"] == c_lbl and p["dbz"] >= 10.0:
                                c["eta_min"] = p["time_offset"]
                                break
                                
                    wind_speed = processor.get_wind_speed_kmh_from_vector(clouds[0]["vx"], clouds[0]["vy"])
                    wind_dir = processor.get_wind_direction_text_from_vector(clouds[0]["vx"], clouds[0]["vy"])
                    percent_change = clouds[0]["growth_rate"] * 100.0
                    # Log telemetry for approaching clouds
                    for c in clouds:
                        log_growth_decay_telemetry(
                            target_label=c.get("label"),
                            dbz_now=float(c.get("dbz_now", 0.0)),
                            dbz_prev=float(c.get("dbz_prev", 0.0)),
                            growth_rate=float(c.get("growth_rate", 0.0)),
                            context="predict_rain_approaching"
                        )
                else:
                    wind_speed = processor.get_wind_speed_kmh(flow, px, py)
                    wind_dir = processor.get_wind_direction_text(flow, px, py)
                    percent_change = 0.0
    
                def render_hq_png(target_frame, pin_x, pin_y, time_utc, proc, raw_bg=None):
                    from PIL import Image, ImageFont, ImageDraw
                    import io
                    import cv2
                    import numpy as np
    
                    # Uncrop to full canvas (e.g. 800×800) so the raw TMD timestamp strip at the bottom is preserved
                    th, tw = target_frame.shape[:2]
                    cfg = proc.config
                    scx = getattr(cfg, "static_crop_x", 0)
                    scy = getattr(cfg, "static_crop_y", 0)
                    full_w = getattr(cfg, "raw_width", 800) or 800
                    full_h = getattr(cfg, "raw_height", 800) or 800
    
                    if raw_bg is not None and raw_bg.shape[:2] == (full_h, full_w):
                        # Use actual raw TMD image containing the authentic bottom timestamp strip & legend
                        canvas = raw_bg.copy()
                        paste_h = min(th, full_h - scy)
                        paste_w = min(tw, full_w - scx)
                        canvas[scy:scy + paste_h, scx:scx + paste_w] = target_frame[:paste_h, :paste_w]
                        full_frame = canvas
                        full_pin_x = pin_x + scx
                        full_pin_y = pin_y + scy
                        logger.info(f"[{station_code}] [RADAR_LATEST_HQ] Embedded into authentic TMD raw canvas ({full_w}x{full_h})")
                    elif th < full_h or tw < full_w:
                        canvas = np.zeros((full_h, full_w, 3), dtype=target_frame.dtype)
                        paste_h = min(th, full_h - scy)
                        paste_w = min(tw, full_w - scx)
                        canvas[scy:scy + paste_h, scx:scx + paste_w] = target_frame[:paste_h, :paste_w]
                        full_frame = canvas
                        full_pin_x = pin_x + scx
                        full_pin_y = pin_y + scy
                    else:
                        full_frame = target_frame
                        full_pin_x = pin_x
                        full_pin_y = pin_y
    
                    # Scale to 3x first (LANCZOS4 or NEAREST)
                    scale = 3.0
                    img_hq_cv = cv2.resize(full_frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
                    # Draw location pin identical to radar_tracking
                    proc.draw_pin_on_frame(img_hq_cv, int(full_pin_x * scale), int(full_pin_y * scale), scale=scale)
                    img_hq = Image.fromarray(img_hq_cv)
    
                    # Add IDC timestamp overlay
                    time_str = time_utc.astimezone(ZoneInfo('Asia/Bangkok')).strftime('%d %b %H:%M')
                    try:
                        fnt = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 120)
                    except Exception:
                        try:
                            fnt = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 140)
                        except Exception:
                            fnt = ImageFont.load_default()
    
                    draw = ImageDraw.Draw(img_hq, "RGBA")
                    if hasattr(draw, 'textbbox'):
                        left, top, right, bottom = draw.textbbox((0, 0), time_str, font=fnt)
                        text_w, text_h = right - left, bottom - top
                    else:
                        text_w, text_h = draw.textsize(time_str, font=fnt)
    
                    x_pos = img_hq.width - text_w - 80
                    y_pos = 80
                    pad = 40
                    draw.rectangle([x_pos - pad, y_pos - pad, x_pos + text_w + pad, y_pos + text_h + pad], fill=(0, 0, 0, 200))
                    draw.text((x_pos, y_pos), time_str, fill=(255, 255, 255, 255), font=fnt)
    
                    static_buffer = io.BytesIO()
                    img_hq.save(static_buffer, format='PNG')
                    return static_buffer.getvalue()
    
                static_bytes = None
                tracking_bytes = None
                timeline_bytes = None
                multiframe_bytes = None
                try:
                    # Fetch raw TMD static image to preserve full authentic background and bottom timestamp strip
                    raw_bg_frame = None
                    try:
                        raw_static_bytes = await processor.fetch_latest_image_bytes(max_retries=1)
                        if raw_static_bytes:
                            _arr = np.frombuffer(raw_static_bytes, np.uint8)
                            _dec = cv2.imdecode(_arr, cv2.IMREAD_COLOR)
                            if _dec is not None:
                                raw_bg_frame = cv2.cvtColor(_dec, cv2.COLOR_BGR2RGB)
                    except Exception as _bg_err:
                        logger.debug(f"Failed to fetch raw TMD static background: {_bg_err}")
    
                    static_bytes = await asyncio.to_thread(render_hq_png, curr_frame.copy(), user_px, user_py, now_utc, processor, raw_bg_frame)
                except Exception as e:
                    logger.error(f"Failed to generate static PNG: {e}")
    
                # Issue #70: Extract historical wind vectors (Ghosting effect 3-5 frames back)
                historical_vectors = []
                target_clusters = clouds if clouds else (all_rain_clusters[:3] if all_rain_clusters else [])
                if len(frames) >= 2 and target_clusters:
                    try:
                        # Extract motion of primary rain cloud centroid across previous frames
                        target_cx, target_cy = target_clusters[0]["cx"], target_clusters[0]["cy"]
                        for f_idx in range(max(0, len(frames) - 5), len(frames) - 1):
                            f_prev = frames[f_idx]
                            f_next = frames[f_idx + 1]
                            f_flow = processor.calculate_optical_flow([f_prev, f_next])
                            if 0 <= target_cx < f_flow.shape[1] and 0 <= target_cy < f_flow.shape[0]:
                                h_vx = float(f_flow[target_cy, target_cx, 0])
                                h_vy = float(f_flow[target_cy, target_cx, 1])
                                historical_vectors.append({
                                    "cx": target_cx,
                                    "cy": target_cy,
                                    "vx": h_vx,
                                    "vy": h_vy
                                })
                    except Exception as e:
                        logger.warning(f"Failed to calculate historical wind vectors: {e}")
    
                try:
                    tracking_bytes = await asyncio.to_thread(
                        processor.generate_radar_tracking_image,
                        curr_frame.copy(), user_px, user_py, clouds, now_utc,
                        all_rain_clusters, predictions, True, get_dev_settings().show_trajectory, show_labels, time_offset_min,
                        locked_target_id,
                        locked_target_cx,
                        locked_target_cy,
                        cluster_dist_approaching=10,
                        cluster_dist_ambient=6,
                        historical_vectors=historical_vectors
                    )
                except Exception as e:
                    logger.error(f"Failed to generate tracking PNG: {e}")
                    
                try:
                    # Create adjusted predictions for the timeline so it displays actual ETA from NOW
                    adjusted_predictions = []
                    for p in predictions:
                        adj_p = p.copy()
                        adj_p["time_offset"] = p["time_offset"] - time_offset_min
                        adjusted_predictions.append(adj_p)
                        
                    timeline_bytes = await asyncio.to_thread(processor.generate_timeline_image, adjusted_predictions, location_name)
                except Exception as e:
                    logger.error(f"Failed to generate timeline PNG: {e}")
                    
                if len(frames) >= 2:
                    try:
                        multiframe_bytes = await asyncio.to_thread(
                            processor.generate_multiframe_analysis_image,
                            frames, flow, user_px, user_py, clouds, processor, now_utc,
                            gap_min, frame_timestamps,
                        )
                    except Exception as e:
                        logger.error(f"Failed to generate multiframe PNG: {e}")
                
                failover_notice = None
                if primary_station and station_code != primary_station:
                    primary_conf = stations_map.get(primary_station)
                    primary_name = getattr(primary_conf, 'name', primary_station) if primary_conf else primary_station
                    used_name = getattr(st_conf, 'name', station_code) if st_conf else station_code
                    logger.warning(f"[FAILOVER] Primary station {primary_station} ({primary_name}) failed. Falling back to station {station_code} ({used_name}).")
                    failover_notice = f"⚠️ *หมายเหตุ:* เรดาร์{primary_name} ({primary_station}) ขัดข้อง/หมดเวลาเชื่อมต่อ ระบบจึงสลับไปใช้เรดาร์{used_name} ({station_code}) แทนชั่วคราว"
    
                logger.info(f"[TMD_RADAR] ✅ Using station={station_code} | frames={len(frames)} | source={frame_source}")
                return {
                    "predictions":       predictions,
                    "intensity":         intensity,
                    "max_rain":          max(p["rain"] for p in predictions) if predictions else 0.0,
                    "max_dbz":           float(max_dbz),
                    "duration_minutes":  sum(15 for p in predictions if p["dbz"] > 0),
                    "wind_speed_kmh":    round(wind_speed, 1),
                    "wind_dir_text":     wind_dir,
                    "endpoint":          f"tmd-radar ({station_code})",
                    "growth_rate_pct":   percent_change,
                    "approaching_clouds": clouds,
                    "all_rain_clusters":  all_rain_clusters,
                    "rain_summary":      summary_line,
                    "is_outdated":       time_offset_min > 45,
                    "failover_notice":   failover_notice,
                    "tracking_mode":     tracking_mode,
                    "locked_target_id":   locked_target_id,
                    "radar_gif_bytes":   None,
                    "radar_hq_gif_bytes": None,
                    "radar_static_bytes": static_bytes,
                    "radar_tracking_bytes": tracking_bytes,
                    "rain_timeline_bytes": timeline_bytes,
                    "radar_multiframe_bytes": multiframe_bytes,
                    "tmd_timestamp_utc": now_utc.isoformat(),
                    "tmd_timestamp_bkk": now_utc.astimezone(ZoneInfo('Asia/Bangkok')).strftime('%d %b %H:%M'),
                }
            except Exception as e:
                logger.warning(f"Failed to process TMD radar {station_code}: {e}")
                pass
    
        raise Exception("Location out of bounds for active TMD Radars.")