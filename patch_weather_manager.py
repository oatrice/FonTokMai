import re

with open("backend/app/services/weather_manager.py", "r") as f:
    content = f.read()

start_pattern = '        for station_code in ["kkn120", "kkn240", "skn240"]:'
end_pattern = '                return {\n                    "predictions":       predictions,'

start_idx = content.find(start_pattern)
end_idx = content.find(end_pattern)

if start_idx != -1 and end_idx != -1:
    new_func = """        for station_code in ["kkn120", "kkn240", "skn240"]:
            try:
                processor = TMDRadarProcessor(station_code)
                px, py = processor.latlng_to_pixel(lat, lng)
                if px is None or py is None:
                    continue

                # Check cache with 10-minute TTL to prevent stale frames across cron runs
                cached_data = self.tmd_frames_cache.get(station_code)
                
                if cached_data and (time.time() - cached_data[2]) < 600:
                    frames, last_modified_dt, flow = cached_data[0], cached_data[1], cached_data[3]
                else:
                    async with get_repo_context() as repo:
                        cache = await repo.get_latest_radar_cache(station_code)
                    
                    if not cache or not cache.get("url_t") or not cache.get("url_t_minus_1"):
                        continue
                        
                    # download images
                    bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "fonmayang.appspot.com")
                    from google.cloud import storage
                    client = storage.Client()
                    bucket = client.bucket(bucket_name)
                    blob_t = bucket.blob(cache["url_t"])
                    blob_t_minus_1 = bucket.blob(cache["url_t_minus_1"])
                    
                    import asyncio
                    try:
                        t_bytes, t_minus_1_bytes = await asyncio.gather(
                            asyncio.to_thread(blob_t.download_as_bytes),
                            asyncio.to_thread(blob_t_minus_1.download_as_bytes)
                        )
                    except Exception as e:
                        logger.error(f"Failed to download frames for {station_code}: {e}")
                        continue
                    
                    import cv2, numpy as np
                    t_np = np.frombuffer(t_bytes, np.uint8)
                    curr_frame = cv2.imdecode(t_np, cv2.IMREAD_COLOR)
                    curr_frame = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2RGB)
                    
                    t_minus_1_np = np.frombuffer(t_minus_1_bytes, np.uint8)
                    prev_frame = cv2.imdecode(t_minus_1_np, cv2.IMREAD_COLOR)
                    prev_frame = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2RGB)
                    
                    frames = [prev_frame, curr_frame]
                    last_modified_dt = datetime.fromtimestamp(cache["timestamp"], timezone.utc)
                    flow = processor.calculate_optical_flow(frames)
                    
                    # Cache it with flow to avoid recalculating
                    self.tmd_frames_cache[station_code] = (frames, last_modified_dt, time.time(), flow)

                if not frames or len(frames) < 2:
                    continue

                curr_frame = frames[-1].copy()
                prev_frame = frames[-2].copy()

                # Find all cloud clusters approaching the user
                clouds = processor.find_approaching_clouds(
                    curr_frame, prev_frame, flow, px, py,
                    search_radius=80, min_dbz=20.0, cluster_dist=20,
                )

                # Apply mock overrides
                if mock_state in ("rain", "storm"):
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
                            bands = [
                                {"color": (46, 204, 113),  "dbz": 25.0, "base_offset": (-5, 5),   "eta": 0},  # Green
                                {"color": (241, 196, 15),  "dbz": 35.0, "base_offset": (-15, 15), "eta": 5},  # Yellow
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
                            cx, cy = px + mc["offset"][0], py + mc["offset"][1]
                            vx, vy = 3.0, -3.0  # Move towards NE
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
                                import cv2
                                cv2.circle(curr_frame, (cx, cy), 22, mc["color"], -1)
                    else:
                        for c in clouds:
                            c["dbz_now"]       = max(c["dbz_now"], 40.0)
                            c["predicted_dbz"] = max(c["predicted_dbz"], 40.0)
                elif mock_state == "clear":
                    clouds = []

                now_utc = last_modified_dt if last_modified_dt else datetime.now(timezone.utc)
                current_utc = datetime.now(timezone.utc)
                time_offset_min = (current_utc - now_utc).total_seconds() / 60.0

                summary_line = processor.render_rain_summary(clouds, confidence_cutoff_min=90, time_offset_min=time_offset_min)

                def dbz_to_intensity(d: float) -> str:
                    if d >= 55: return "ฝนตกหนักมาก"
                    if d >= 35: return "ฝนตกหนัก"
                    if d >= 20: return "ฝนตกปานกลาง"
                    if d > 0:   return "ฝนตกเล็กน้อย"
                    return "ไม่มีฝน"

                predictions = []
                max_dbz = 0.0
                current_dbz = processor.get_dbz_at_pixel(curr_frame, px, py)
                
                for steps in range(5):
                    offset_min = steps * 15
                    if steps == 0:
                        dbz = current_dbz
                    else:
                        dbz = 0.0
                        window_min = offset_min - 7.5
                        window_max = offset_min + 7.5
                        for c in clouds:
                            if window_min <= c["eta_min"] < window_max:
                                if c["predicted_dbz"] > dbz:
                                    dbz = c["predicted_dbz"]
                                    
                    if mock_state == "rain":
                        dbz = max(dbz, 40.0)
                    elif mock_state == "clear":
                        dbz = 0.0
                        
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
                    })

                current_dbz = predictions[0]["dbz"]
                intensity   = predictions[0]["intensity"]
                
                if clouds:
                    wind_speed = processor.get_wind_speed_kmh_from_vector(clouds[0]["vx"], clouds[0]["vy"])
                    wind_dir = processor.get_wind_direction_text_from_vector(clouds[0]["vx"], clouds[0]["vy"])
                    percent_change = clouds[0]["growth_rate"] * 100.0
                else:
                    wind_speed = processor.get_wind_speed_kmh(flow, px, py)
                    wind_dir = processor.get_wind_direction_text(flow, px, py)
                    percent_change = 0.0

                async def render_hq_png():
                    from PIL import Image, ImageFont, ImageDraw
                    import cv2
                    # Copy to avoid mutating original for future tasks
                    cf = curr_frame.copy()
                    processor.draw_pin_on_frame(cf, px, py)
                    img_orig = Image.fromarray(cf)
                    img_hq = img_orig.resize((int(img_orig.width * 3.0), int(img_orig.height * 3.0)), Image.Resampling.NEAREST)
                    
                    time_str = now_utc.astimezone(ZoneInfo('Asia/Bangkok')).strftime('%d %b %H:%M')
                    try:
                        fnt = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 96)
                    except:
                        try:
                            fnt = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 96)
                        except:
                            fnt = ImageFont.load_default()
                            
                    draw = ImageDraw.Draw(img_hq, "RGBA")
                    left, top, right, bottom = draw.textbbox((0, 0), time_str, font=fnt)
                    text_w, text_h = right - left, bottom - top
                    
                    x_pos = img_hq.width - text_w - 30
                    y_pos = 30
                    pad = 15
                    draw.rectangle([x_pos-pad, y_pos-pad, x_pos+text_w+pad, y_pos+text_h+pad], fill=(0, 0, 0, 200))
                    draw.text((x_pos, y_pos), time_str, fill=(255, 255, 255, 255), font=fnt)
                    
                    import io
                    static_buffer = io.BytesIO()
                    img_hq.save(static_buffer, format='PNG')
                    return static_buffer.getvalue()

                static_bytes = None
                tracking_bytes = None
                timeline_bytes = None
                try:
                    import asyncio
                    static_bytes = await asyncio.to_thread(render_hq_png)
                    tracking_bytes = await asyncio.to_thread(processor.generate_radar_tracking_image, curr_frame.copy(), px, py, clouds)
                    timeline_bytes = await asyncio.to_thread(processor.generate_timeline_image, clouds)
                except Exception as e:
                    logger.error(f"Failed to generate radar PNGs: {e}")
                
                # Cleanup memory
                del curr_frame
                del prev_frame
                import gc
                gc.collect()

                return {
                    "predictions":       predictions,"""
    new_content = content[:start_idx] + new_func + content[end_idx + len('                return {\n                    "predictions":       predictions,'):]
    with open("backend/app/services/weather_manager.py", "w") as out_f:
        out_f.write(new_content)
    print("Patched weather_manager.py successfully!")
else:
    print(f"Could not find patterns! Start: {start_idx}, End: {end_idx}")
