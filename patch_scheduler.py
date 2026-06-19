import re

with open("backend/app/scheduler_tasks.py", "r") as f:
    content = f.read()

def extract_loop_body():
    # We will just replace the entire check_rain_and_alert function.
    pass

# Read the original file
lines = content.split('\n')
start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if line.startswith("async def check_rain_and_alert():"):
        start_idx = i
    elif line.startswith("async def check_disasters_frequent_routine():"):
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    original_func = lines[start_idx:end_idx]
    
    # We will create the new functions
    new_funcs = """import asyncio

async def _process_location(loc, repo, weather_manager, now, sem):
    async with sem:
        try:
            alerts_sent = 0
            errors = 0
            severity_escalated = False
            if loc.last_alerted_at:
                time_since_last_alert = now - loc.last_alerted_at
                if time_since_last_alert < timedelta(minutes=ALERT_COOLDOWN_MINUTES):
                    try:
                        mock_state_pre = await repo.get_mock_state(loc.chat_id)
                        pre_result = await weather_manager.predict_rain(loc.latitude, loc.longitude, mock_state=mock_state_pre)
                        current_max_rain = pre_result.get("max_rain", 0.0)
                        last_max_rain = loc.last_alert_max_rain or 0.0

                        if current_max_rain > last_max_rain and current_max_rain >= RAIN_TRIGGER_THRESHOLD_MM:
                            logger.info(
                                f"Smart Cooldown override for chat_id {loc.chat_id}: "
                                f"rain {last_max_rain:.1f} → {current_max_rain:.1f} mm/hr"
                            )
                            severity_escalated = True
                            result = pre_result
                        elif last_max_rain > 0.0 and current_max_rain < RAIN_TRIGGER_THRESHOLD_MM:
                            logger.info(f"Smart Cooldown override (All-Clear) for chat_id {loc.chat_id}")
                            result = pre_result
                        else:
                            logger.debug(
                                f"Skipping chat_id {loc.chat_id} (cooldown, "
                                f"rain {current_max_rain:.1f} mm/hr ≤ last {last_max_rain:.1f} mm/hr)"
                            )
                            return 0, 0
                    except Exception as e:
                        logger.warning(f"Smart Cooldown pre-check failed for {loc.chat_id}: {e}. Skipping.")
                        return 0, 0

            if not severity_escalated:
                mock_state = await repo.get_mock_state(loc.chat_id)
                result = await weather_manager.predict_rain(loc.latitude, loc.longitude, mock_state=mock_state)

            max_rain = result.get("max_rain", 0.0)
            if max_rain < RAIN_TRIGGER_THRESHOLD_MM:
                if loc.last_alert_max_rain and loc.last_alert_max_rain > 0.0:
                    logger.info(f"Sending All-Clear alert for chat_id {loc.chat_id}")
                    loc_name_str = f" '{loc.name.capitalize()}' " if loc.name and loc.name.lower() != "default" else " "
                    text = f"☀️ สภาพอากาศ ณ พิกัด{loc_name_str}เคลียร์แล้ว\\n(ไม่มีแนวโน้มฝนตกในขณะนี้)"
                    await send_telegram_message(loc.chat_id, text)
                    await repo.update_last_alerted(loc, now, max_rain=0.0)
                else:
                    logger.debug(f"Skipping alert for {loc.chat_id}: Max rain {max_rain} mm/hr < threshold {RAIN_TRIGGER_THRESHOLD_MM}")
                return 0, 0

            predictions = result.get("predictions", [])
            eta_minutes = None
            rain_start_dt = None

            if predictions:
                try:
                    base_time = datetime.fromisoformat(predictions[0].get("time", "").replace("Z", "+00:00"))
                except Exception:
                    base_time = None
                    
                for pred in predictions:
                    if pred.get("rain", 0) >= RAIN_TRIGGER_THRESHOLD_MM:
                        if base_time:
                            try:
                                pred_time = datetime.fromisoformat(pred.get("time", "").replace("Z", "+00:00"))
                                current_utc = datetime.now(timezone.utc)
                                eta_minutes = int((pred_time - current_utc).total_seconds() / 60)
                                if eta_minutes < 0:
                                    eta_minutes = 0
                                rain_start_dt = pred_time
                            except Exception:
                                eta_minutes = 0
                        else:
                            eta_minutes = 0
                        break

            if eta_minutes is not None and eta_minutes <= 60:
                intensity_str = result.get("intensity", "ไม่ทราบ")
                duration_min = result.get("duration_minutes", 0)
                wind_speed_kmh = result.get("wind_speed_kmh", 0.0)
                endpoint_source = result.get("endpoint", "unknown")
                
                source_name = endpoint_source
                if endpoint_source == "tomorrow": source_name = "Tomorrow.io"
                elif endpoint_source == "rainbow-local": source_name = "Rainbow (Local)"
                elif endpoint_source == "rainbow-global": source_name = "Rainbow (Global)"
                
                loc_name_str = f" '{loc.name.capitalize()}' " if loc.name and loc.name.lower() != "default" else " "
                
                if not rain_start_dt:
                    rain_start_dt = datetime.now(timezone.utc) + timedelta(minutes=eta_minutes)
                    
                rain_end_dt = rain_start_dt + timedelta(minutes=duration_min)
                start_time_str = rain_start_dt.astimezone(BKK_TZ).strftime("%H:%M น.")
                end_time_str = rain_end_dt.astimezone(BKK_TZ).strftime("%H:%M น.")
                distance_km = (eta_minutes / 60.0) * wind_speed_kmh
                
                text = ""
                if severity_escalated:
                    last_rain_val = loc.last_alert_max_rain or 0.0
                    text += f"⚠️ *อัปเดต: ฝนทวีความรุนแรงขึ้น!*\\n({last_rain_val:.1f} mm/hr → {max_rain:.1f} mm/hr)\\n\\n"

                if eta_minutes == 0: text += f"🌧️ ฝนกำลังตกอยู่ที่พิกัด{loc_name_str}ของคุณ ณ ขณะนี้\\n"
                else:
                    text += f"🌧️ ฝนกำลังเคลื่อนมาทางพิกัด{loc_name_str}ของคุณ\\n"
                    text += f"⏰ จะเริ่มตกเวลา: {start_time_str} (ในอีก {eta_minutes} นาที)\\n"
                
                duration_text = f"ตกต่อเนื่อง {duration_min} นาที"
                if duration_min >= 60:
                    hrs = duration_min // 60
                    mins = duration_min % 60
                    duration_text = f"ตกต่อเนื่อง {hrs} ชม. {mins} นาที" if mins > 0 else f"ตกต่อเนื่อง {hrs} ชม."
                    
                if duration_min > 0: text += f"🛑 คาดว่าจะหยุดเวลา: {end_time_str} ({duration_text})\\n\\n"
                else: text += "\\n"
                    
                if intensity_str == "ไม่มีฝน" and eta_minutes > 0:
                    if max_rain > 10.0: max_int = "ฝนตกหนักมาก"
                    elif max_rain > 2.5: max_int = "ฝนตกหนัก"
                    elif max_rain > 0.5: max_int = "ฝนตกปานกลาง"
                    else: max_int = "ฝนตกเล็กน้อย"
                    text += f"💧 ความรุนแรง (สูงสุด): {max_int} ({max_rain:.1f} mm/hr)\\n"
                else:
                    text += f"💧 ความรุนแรง: {intensity_str} ({max_rain:.1f} mm/hr)\\n"
                
                wind_dir_text = result.get("wind_dir_text", "ไม่ทราบ")
                if wind_speed_kmh > 0: text += f"🌬️ สภาพลม: {wind_speed_kmh:.1f} km/h (พัดไปทางทิศ {wind_dir_text})\\n"
                if eta_minutes > 0 and wind_speed_kmh > 0: text += f"📏 ระยะห่างจากกลุ่มฝน: ประมาณ {distance_km:.1f} กม.\\n"
                    
                rain_summary = result.get("rain_summary")
                if rain_summary:
                    text += f"{rain_summary}\\n"
                else:
                    growth_rate = result.get("growth_rate_pct")
                    if growth_rate is not None:
                        if growth_rate > 5.0: text += f"📈 แนวโน้มกลุ่มฝน: กำลังก่อตัวแรงขึ้น (+{growth_rate:.1f}%)\\n"
                        elif growth_rate < -5.0: text += f"📉 แนวโน้มกลุ่มฝน: อ่อนกำลังลง ({growth_rate:.1f}%)\\n"
                        else: text += f"➖ แนวโน้มกลุ่มฝน: คงที่\\n"
                        
                text += f"📡 แหล่งข้อมูล: {source_name}\\n"
                bkk_tz = timezone(timedelta(hours=7))
                update_time_str = datetime.now(bkk_tz).strftime("%d/%m/%Y %H:%M:%S")
                text += f"🔄 ข้อมูลอัปเดตล่าสุด: {update_time_str}\\n"
                    
                is_dev = str(loc.chat_id) in DEVELOPER_CHAT_IDS
                reply_markup = get_radar_inline_keyboard(loc.latitude, loc.longitude, is_developer=is_dev)
                
                r_lat = round(loc.latitude, 4)
                r_lng = round(loc.longitude, 4)
                reply_markup["inline_keyboard"].append([{"text": "📊 เทียบข้อมูล", "callback_data": f"compare_api_{r_lat}_{r_lng}"}])
                ep_map = {"tomorrow": "t", "rainbow-local": "rl", "rainbow-global": "rg", "xweather": "xw", "open-meteo": "om"}
                ep_code = ep_map.get(result.get("endpoint"), "u")
                cb_data = f"fb_falsealarm_{r_lat}_{r_lng}_{ep_code}_{max_rain:.1f}"
                reply_markup["inline_keyboard"].append([{"text": "❌ แจ้งเตือนผิดพลาด (ฝนไม่ตกจริง)", "callback_data": cb_data}])
                
                logger.info(f"Alerting chat_id {loc.chat_id}: ETA {eta_minutes} mins")
                await send_telegram_message(loc.chat_id, text, reply_markup=reply_markup)
                
                gif_bytes = result.get("radar_gif_bytes")
                static_bytes = result.get("radar_static_bytes")
                tracking_bytes = result.get("radar_tracking_bytes")
                timeline_bytes = result.get("rain_timeline_bytes")
                
                if static_bytes: await send_telegram_photo(loc.chat_id, static_bytes, "radar_latest.png")
                if timeline_bytes: await send_telegram_photo(loc.chat_id, timeline_bytes, "rain_timeline.png")
                if tracking_bytes: await send_telegram_photo(loc.chat_id, tracking_bytes, "radar_tracking.png")
                if gif_bytes: await send_telegram_document(loc.chat_id, gif_bytes, "radar_nowcast.gif")
                
                await repo.update_last_alerted(loc, now, max_rain=max_rain)
                
                try:
                    advanced_data = await weather_manager.get_advanced_alerts(loc.latitude, loc.longitude, mock_state=mock_state)
                    has_advisory = len(advanced_data.get("advisories", [])) > 0
                    has_lightning = advanced_data.get("lightning") is not None
                    has_stormcell = advanced_data.get("stormcell") is not None
                    
                    if has_advisory or has_lightning or has_stormcell:
                        adv_text = "🚨 *ข้อมูลเตือนภัยขั้นสูงรอบตัวคุณ*\\n\\n"
                        if has_advisory:
                            for adv in advanced_data["advisories"]: adv_text += f"⚠️ ประกาศเตือนภัย: {adv.get('name', '')}\\n"
                            adv_text += "\\n"
                        if has_lightning:
                            lightning = advanced_data["lightning"]
                            adv_text += f"⚡ ฟ้าผ่าระยะใกล้สุด: {lightning.get('distance_km', 0):.1f} กม.\\n\\n"
                        if has_stormcell:
                            stormcell = advanced_data["stormcell"]
                            if stormcell.get('distance_km') is None:
                                adv_text += f"🌪️ แนวโน้มกลุ่มฝน/ลม (Contingency):\\n"
                                adv_text += f"   - ทิศทาง: {stormcell.get('direction', 'N/A')}\\n"
                                adv_text += f"   - ความเร็วลม: {stormcell.get('speed_kmh', 0):.1f} km/h\\n\\n"
                                adv_text += "ℹ️ ข้อมูลขั้นสูงจาก Open-Meteo (Fallback)"
                            else:
                                adv_text += f"🌪️ ตรวจพบกลุ่มพายุ: ระยะห่าง {stormcell.get('distance_km', 0):.1f} กม.\\n"
                                adv_text += f"   - ทิศทาง: {stormcell.get('direction', 'N/A')}\\n"
                                adv_text += f"   - ความเร็ว: {stormcell.get('speed_kmh', 0):.1f} km/h\\n"
                                adv_text += f"   - ความรุนแรงสูงสุด (dBZ): {stormcell.get('max_dbz', 0)}\\n\\n"
                                adv_text += "ℹ️ ข้อมูลขั้นสูงจาก Xweather"
                        elif has_advisory or has_lightning:
                            adv_text += "ℹ️ ข้อมูลขั้นสูงจาก Xweather"
                        await send_telegram_message(loc.chat_id, adv_text)
                except Exception as e:
                    logger.error(f"Failed to process advanced alerts for {loc.chat_id}: {e}")
                    errors += 1
                
                alerts_sent += 1
                return alerts_sent, errors

            return 0, 0
        except Exception as e:
            logger.error(f"Failed to check rain for chat_id {loc.chat_id}: {e}")
            return 0, 1


async def check_rain_and_alert():
    logger.info("Starting proactive rain check...")
    start_time = time.time()
    alerts_sent = 0
    errors = 0
    
    try:
        await fetch_tmd_radar_routine()
    except Exception as e:
        logger.error(f"Error during cache phase: {e}")
    
    async with get_repo_context() as repo:
        locations = await repo.get_active_locations()
        if not locations:
            logger.info("No active locations to check.")
            return

        weather_manager = WeatherManager()
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        sem = asyncio.Semaphore(15)
        tasks = [_process_location(loc, repo, weather_manager, now, sem) for loc in locations]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for r in results:
            if isinstance(r, tuple):
                alerts_sent += r[0]
                errors += r[1]
            elif isinstance(r, Exception):
                logger.error(f"Task raised an unhandled exception: {r}")
                errors += 1
                
        duration_s = time.time() - start_time
        try:
            metrics_svc = MetricsService(repo)
            await metrics_svc.record_cron_run(
                routine_name="check_rain",
                duration_s=duration_s,
                alerts_sent=alerts_sent,
                locations_checked=len(locations),
                errors=errors
            )
        except Exception as e:
            logger.error(f"Failed to save metrics for check_rain: {e}")
"""

    new_content = "\n".join(lines[:start_idx]) + "\n\n" + new_funcs + "\n\n" + "\n".join(lines[end_idx:])
    
    with open("backend/app/scheduler_tasks.py", "w") as out_f:
        out_f.write(new_content)
    print("Patched scheduler_tasks.py successfully!")
else:
    print("Could not find start or end indices!")

