from fastapi import Request, BackgroundTasks
import os
import json
import subprocess
from app.services.command_router import router as cmd_router
from .webhook_utils import (
    _reply, LAST_ACTIVE_LOCATION, LAST_PINNED_LOCATION,
    get_repo_context, logger, log_audit_event, check_admin_access
)
from app.services import telegram
from .webhook_location import process_telegram_location
from app.services.tmd_radar_config import STATIONS
from app.services.tmd_radar_processor import TMDRadarProcessor
from app.services import weather_manager
import re
import math
from datetime import datetime, timezone

@cmd_router.bind("/lock ", requires_admin=True, task_route="worker/handle-lock", loading_text="⏳ กำลังประมวลผล...")
async def handle_lock_command(chat_id: int, command: str, message_id_to_edit: int = None):
    import re
    cx, cy = None, None
    grid_lbl = None
    grid_col_idx = None
    grid_row_idx = None
    
    try:
        async with get_repo_context() as repo:
            locs = await repo.get_user_locations(chat_id)
            if not locs:
                await _reply(chat_id, "⚠️ ไม่พบข้อมูลพิกัดหลักของคุณ กรุณาส่งพิกัดก่อนใช้งานคำสั่งนี้", message_id_to_edit)
                return
            
            raw_args = command.removeprefix("/lock").strip()
            args = raw_args.split()
            if not args:
                error_msg = (
                    "⚠️ รูปแบบคำสั่งไม่ถูกต้อง\n"
                    "กรุณาใช้:\n"
                    "- ล็อคช่องตาราง: `/lock [ชื่อพิกัด] D2` หรือ `/lock D2`\n"
                    "- ล็อคพิกัดจริง: `/lock [ชื่อพิกัด] 13.75 100.5` หรือ `/lock 13.75 100.5`"
                )
                await _reply(chat_id, error_msg, message_id_to_edit)
                return
                
            first_arg = args[0].lower()
            matched_loc = None
            for l in locs:
                if l.name.lower() == first_arg:
                    matched_loc = l
                    break
                    
            if matched_loc:
                loc = matched_loc
                target_str = " ".join(args[1:])
            else:
                loc = None
                # If there's a recently pinned Telegram location, always prioritize it!
                pinned = LAST_PINNED_LOCATION.get(chat_id)
                if pinned:
                    pinned_lat, pinned_lng = pinned
                    loc = await repo.save_location(
                        chat_id, pinned_lat, pinned_lng, "FOREVER", name="default"
                    )
                    LAST_ACTIVE_LOCATION[chat_id] = "default"
                else:
                    active_loc_name = LAST_ACTIVE_LOCATION.get(chat_id)
                    if active_loc_name:
                        for l in locs:
                            if l.name.lower() == active_loc_name.lower():
                                loc = l
                                break
                if not loc:
                    for name_to_find in ["home", "default", "work"]:
                        for l in locs:
                            if l.name.lower() == name_to_find:
                                loc = l
                                break
                        if loc:
                            break
                if not loc:
                    loc = locs[0]
                target_str = raw_args
                
            lat, lng = loc.latitude, loc.longitude
            loc_name = loc.name
            prev_cx = loc.locked_target_cx
            prev_cy = loc.locked_target_cy
        
        grid_match = re.match(r"^([a-hA-H])[-_]?([1-8])$", target_str.strip())
        cloud_label_match = re.match(r"^[a-zA-Z]{1,2}$", target_str.strip())
        
        is_grid_lock = False
        is_label_lock = False
        
        if grid_match:
            is_grid_lock = True
            col_char = grid_match.group(1).upper()
            row_char = grid_match.group(2)
            grid_col_idx = ord(col_char) - ord('A')
            grid_row_idx = int(row_char) - 1
            cx = int((grid_col_idx + 0.5) * 100)
            cy = int((grid_row_idx + 0.5) * 100)
            grid_lbl = f"{col_char}{row_char}"
        elif cloud_label_match:
            is_label_lock = True
            grid_lbl = target_str.strip().upper()
        else:
            parts = re.findall(r"[-+]?\d*\.\d+|\d+", target_str)
            if len(parts) < 2:
                error_msg = (
                    "⚠️ รูปแบบตัวชี้เป้าไม่ถูกต้อง\n"
                    "กรุณาใช้:\n"
                    "- ล็อคกลุ่มฝน: `/lock [ชื่อพิกัด] A` หรือ `/lock A`\n"
                    "- ล็อคช่องตาราง: `/lock [ชื่อพิกัด] D4`\n"
                    "- ล็อคพิกัดจริง: `/lock [ชื่อพิกัด] 13.75 100.5`"
                )
                await _reply(chat_id, error_msg, message_id_to_edit)
                return
            
            val1 = float(parts[0])
            val2 = float(parts[1])
            is_latlng = (5.0 <= val1 <= 25.0) and (95.0 <= val2 <= 107.0)
            
            if is_latlng:
                cx, cy = None, None
            else:
                cx, cy = int(val1), int(val2)
                
        import math
        from app.services import weather_manager
        from app.services.tmd_radar_processor import TMDRadarProcessor
        from app.services.tmd_radar_config import STATIONS

        def station_distance(station_code: str) -> float:
            conf = STATIONS[station_code]
            return math.hypot(lat - conf.center_lat, lng - conf.center_lng)

        wm = weather_manager.WeatherManager()
        processor = None
        station_code = None
        
        last_used = weather_manager.WeatherManager.LAST_USED_STATION.get(int(chat_id))
        candidates = ["kkn120", "kkn240", "skn240"]
        if last_used and last_used in candidates:
            candidates_to_check = [last_used] + [c for c in sorted(candidates, key=station_distance) if c != last_used]
        else:
            candidates_to_check = sorted(candidates, key=station_distance)

        for candidate in candidates_to_check:
            candidate_processor = TMDRadarProcessor(candidate)
            user_px, user_py = candidate_processor.latlng_to_pixel(lat, lng, is_loop=False)
            if user_px is not None and user_py is not None:
                # Load cache to verify if this station has at least 2 frames (meaning it is functional)
                try:
                    c_data = await wm.load_persistent_cache_to_memory(candidate, candidate_processor)
                    if c_data and len(c_data[0]) >= 2:
                        processor = candidate_processor
                        station_code = candidate
                        break
                except Exception:
                    pass

        if processor is None or station_code is None:
            # Fallback to the closest station that supports the user coordinate bounding box
            for candidate in candidates_to_check:
                candidate_processor = TMDRadarProcessor(candidate)
                user_px, user_py = candidate_processor.latlng_to_pixel(lat, lng, is_loop=False)
                if user_px is not None and user_py is not None:
                    processor = candidate_processor
                    station_code = candidate
                    break

        if processor is None or station_code is None:
            await _reply(chat_id, "⚠️ พิกัดหลักอยู่นอกขอบเขตของแผนที่เรดาร์", message_id_to_edit)
            return

        if not grid_lbl and "parts" in locals() and len(parts) >= 2:
            val1 = float(parts[0])
            val2 = float(parts[1])
            is_latlng = (5.0 <= val1 <= 25.0) and (95.0 <= val2 <= 107.0)
            if is_latlng:
                cx, cy = processor.latlng_to_pixel(val1, val2, is_loop=False)

        cache_data = await wm.load_persistent_cache_to_memory(station_code, processor)
        
        has_cloud = False
        max_dbz = 0.0
        peak_x, peak_y = cx, cy
        vx, vy = 0.0, 0.0
        frame_w = processor.config.static_crop_width
        frame_h = processor.config.static_crop_height
        
        if cache_data:
            frames, _, _, flow, _, _, _ = cache_data
            latest_frame = frames[-1]
            h, w = latest_frame.shape[:2]
            frame_w, frame_h = w, h
            
            if is_grid_lock:
                user_px, user_py = processor.latlng_to_pixel(lat, lng, is_loop=False)
                crop_r = 120
                crop_x1 = max(0, user_px - crop_r)
                crop_y1 = max(0, user_py - crop_r)
                crop_x2 = min(w, user_px + crop_r)
                crop_y2 = min(h, user_py + crop_r)
                cell_w = (crop_x2 - crop_x1) / 8.0
                cell_h = (crop_y2 - crop_y1) / 8.0
                x_min = max(0, int(crop_x1 + grid_col_idx * cell_w))
                x_max = min(w, int(crop_x1 + (grid_col_idx + 1) * cell_w))
                y_min = max(0, int(crop_y1 + grid_row_idx * cell_h))
                y_max = min(h, int(crop_y1 + (grid_row_idx + 1) * cell_h))
                cx = int((x_min + x_max) / 2)
                cy = int((y_min + y_max) / 2)
                peak_x, peak_y = cx, cy
                
                for y_p in range(y_min, y_max):
                    for x_p in range(x_min, x_max):
                        dbz = processor.get_dbz_at_pixel(latest_frame, x_p, y_p)
                        if dbz >= 10.0:
                            has_cloud = True
                            if dbz > max_dbz:
                                max_dbz = dbz
                                peak_x, peak_y = x_p, y_p
                                
                if has_cloud:
                    cx, cy = peak_x, peak_y
                    vx = float(flow[peak_y, peak_x, 0])
                    vy = float(flow[peak_y, peak_x, 1])
            elif is_label_lock:
                res = await wm.predict_rain(lat, lng, chat_id=chat_id)
                clouds = res.get("approaching_clouds", [])
                all_clusters = res.get("all_rain_clusters", [])
                
                target_c = None
                for c in clouds:
                    if c.get("label", "").upper() == grid_lbl:
                        target_c = c
                        break
                if not target_c:
                    for c in all_clusters:
                        if c.get("label", "").upper() == grid_lbl:
                            target_c = c
                            break
                            
                if target_c:
                    cx = target_c["cx"]
                    cy = target_c["cy"]
                    has_cloud = True
                    max_dbz = target_c.get("dbz_now", 0.0)
                    peak_x, peak_y = cx, cy
                    vx = float(flow[cy, cx, 0])
                    vy = float(flow[cy, cx, 1])
                else:
                    error_msg = f"⚠️ ไม่พบกลุ่มฝนป้ายกำกับ [{grid_lbl}] ในบริเวณรอบตัวคุณ หรือเมฆสลายตัวไปแล้ว"
                    await _reply(chat_id, error_msg, message_id_to_edit)
                    return
            else:
                search_radius = 25
                x_min = max(0, cx - search_radius)
                x_max = min(w, cx + search_radius)
                y_min = max(0, cy - search_radius)
                y_max = min(h, cy + search_radius)
                
                for y_p in range(y_min, y_max):
                    for x_p in range(x_min, x_max):
                        dbz = processor.get_dbz_at_pixel(latest_frame, x_p, y_p)
                        if dbz >= 10.0:
                            has_cloud = True
                            if dbz > max_dbz:
                                max_dbz = dbz
                                peak_x, peak_y = x_p, y_p
                                
                if has_cloud:
                    cx, cy = peak_x, peak_y
                    vx = float(flow[peak_y, peak_x, 0])
                    vy = float(flow[peak_y, peak_x, 1])
        elif is_grid_lock:
            user_px, user_py = processor.latlng_to_pixel(lat, lng, is_loop=False)
            crop_r = 120
            crop_x1 = max(0, user_px - crop_r)
            crop_y1 = max(0, user_py - crop_r)
            crop_x2 = min(frame_w, user_px + crop_r)
            crop_y2 = min(frame_h, user_py + crop_r)
            cell_w = (crop_x2 - crop_x1) / 8.0
            cell_h = (crop_y2 - crop_y1) / 8.0
            cx = int(crop_x1 + (grid_col_idx + 0.5) * cell_w)
            cy = int(crop_y1 + (grid_row_idx + 0.5) * cell_h)
            peak_x, peak_y = cx, cy

        if cx is None or cy is None or not (0 <= cx < frame_w and 0 <= cy < frame_h):
            await _reply(chat_id, "⚠️ พิกัดอยู่นอกขอบเขตของแผนที่เรดาร์", message_id_to_edit)
            return

        eta_text = ""
        comparison_text = ""
        avg_vx, avg_vy = vx, vy
        if is_label_lock and 'target_c' in locals() and target_c:
            avg_vx = target_c.get("vx", vx)
            avg_vy = target_c.get("vy", vy)

        wind_speed = 0.0
        wind_dir = "ไม่ทราบ"
        avg_wind_speed = 0.0
        avg_wind_dir = "ไม่ทราบ"
        
        if has_cloud:
            user_px, user_py = processor.latlng_to_pixel(lat, lng)
            dx = user_px - peak_x
            dy = user_py - peak_y
            dist = math.sqrt(dx*dx + dy*dy)
            
            wind_speed = processor.get_wind_speed_kmh_from_vector(vx, vy)
            wind_dir = processor.get_wind_direction_text_from_vector(vx, vy)
            avg_wind_speed = processor.get_wind_speed_kmh_from_vector(avg_vx, avg_vy)
            avg_wind_dir = processor.get_wind_direction_text_from_vector(avg_vx, avg_vy)
            
            if dist > 0:
                v_close = (vx * dx + vy * dy) / dist
            else:
                v_close = 0
                
            if v_close > 0.05:
                t_mins = int((dist / v_close) * 15)
                if t_mins >= 60:
                    hrs = t_mins // 60
                    mins = t_mins % 60
                    eta_text = f"⏱️ คาดว่าจะเคลื่อนเข้าหาคุณในอีกประมาณ: {hrs} ชม. {mins} นาที\n"
                else:
                    eta_text = f"⏱️ คาดว่าจะเคลื่อนเข้าหาคุณในอีกประมาณ: {t_mins} นาที\n"
            else:
                eta_text = f"💨 แนวโน้มเคลื่อนที่: ขนานหรือออกห่างจากตำแหน่งคุณ (ตามเส้นสีเขียว)\n"
                
            if prev_cx is not None and prev_cy is not None:
                prev_dist = math.sqrt((user_px - prev_cx)**2 + (user_py - prev_cy)**2)
                lon_diff = processor.config.bbox.lng_max - processor.config.bbox.lng_min
                width_km = lon_diff * 111.0
                km_per_pixel = width_km / 800.0
                
                delta_km = (prev_dist - dist) * km_per_pixel
                if delta_km > 0.1:
                    comparison_text = f"📈 เมื่อเทียบกับรอบก่อนหน้า: กลุ่มฝนขยับเข้าใกล้คุณมากขึ้น {delta_km:.1f} กม. (เร็วขึ้น/กระชั้นชิดขึ้น)\n"
                elif delta_km < -0.1:
                    comparison_text = f"📉 เมื่อเทียบกับรอบก่อนหน้า: กลุ่มฝนขยับห่างออกไป {abs(delta_km):.1f} กม.\n"
                else:
                    comparison_text = f"📊 เมื่อเทียบกับรอบก่อนหน้า: อยู่ห่างที่ระยะใกล้เคียงเดิม\n"

        async with get_repo_context() as repo:
            await repo.update_tracking_mode(
                chat_id=chat_id,
                tracking_mode="manual",
                locked_target_id=grid_lbl or "MANUAL",
                locked_target_cx=cx,
                locked_target_cy=cy,
                name=loc_name
            )
            
        if not has_cloud:
            success_msg = f"⚠️ สังเกตการณ์: ไม่พบกลุ่มเมฆฝนในช่องตาราง {grid_lbl or target_str} (ความแรงฝน < 10 dBZ)\n"
            success_msg += f"ตำแหน่งเป้าหมาย: {loc_name.capitalize()}\n"
            success_msg += "ระบบได้บันทึกพิกัดเป้าเล็งไว้แล้ว (คุณสามารถเช็คภาพเรดาร์ล่าสุดเพื่อยืนยัน)"
        else:
            success_msg = f"🔒 ตั้งค่าล็อคเป้าแมนนวลสำเร็จ!\n"
            if is_label_lock:
                success_msg += f"กลุ่มฝน: [{grid_lbl}] (Pixel: {cx}, {cy})\n"
            elif grid_lbl:
                success_msg += f"ช่องตาราง: {grid_lbl} (Pixel: {cx}, {cy})\n"
            else:
                success_msg += f"พิกัดเรดาร์: Pixel ({cx}, {cy})\n"
            success_msg += f"ตำแหน่งเป้าหมาย: {loc_name.capitalize()}\n\n"
            success_msg += f"🔍 ข้อมูลกลุ่มฝนในพื้นที่ล็อคเป้า:\n"
            success_msg += f"  💧 ความแรงฝนสูงสุด: {max_dbz:.1f} dBZ\n"
            success_msg += f"  🌬️ ความเร็วลมเฉลี่ยกลุ่มเมฆ: {avg_wind_speed:.1f} กม./ชม. (ทิศ {avg_wind_dir})\n"
            success_msg += f"  💨 ความเร็วลมสูงสุด: {wind_speed:.1f} กม./ชม. (ทิศ {wind_dir})\n"
            if eta_text:
                success_msg += f"  {eta_text}"
            if comparison_text:
                success_msg += f"  {comparison_text}"
            success_msg += "\nระบบจะใช้ข้อมูลนี้ในการพยากรณ์รอบถัดไป"
        
        await _reply(chat_id, success_msg, message_id_to_edit)
        await process_telegram_location(chat_id, lat, lng, location_name=loc_name, is_lock_command=True)
    except Exception as e:
        logger.error(f"Error handling lock command: {e}")
        await _reply(chat_id, f"❌ เกิดข้อผิดพลาด: {str(e)}", message_id_to_edit)


@cmd_router.bind("/unlock", requires_admin=True, task_route="worker/handle-unlock", loading_text="⏳ กำลังประมวลผล...")
async def handle_unlock_command(chat_id: int, command: str, message_id_to_edit: int = None):
    try:
        async with get_repo_context() as repo:
            locs = await repo.get_user_locations(chat_id)
            if not locs:
                await _reply(chat_id, "⚠️ ไม่พบข้อมูลพิกัดหลักของคุณ", message_id_to_edit)
                return
                
            arg = command.removeprefix("/unlock").strip().lower()
            loc = None
            if arg:
                for l in locs:
                    if l.name.lower() == arg:
                        loc = l
                        break
                        
            if not loc:
                active_loc_name = LAST_ACTIVE_LOCATION.get(chat_id)
                if active_loc_name:
                    for l in locs:
                        if l.name.lower() == active_loc_name.lower():
                            loc = l
                            break
                if not loc:
                    for name_to_find in ["home", "default", "work"]:
                        for l in locs:
                            if l.name.lower() == name_to_find:
                                loc = l
                                break
                        if loc:
                            break
                if not loc:
                    loc = locs[0]
                    
            await repo.update_tracking_mode(
                chat_id=chat_id,
                tracking_mode="auto",
                name=loc.name
            )
            lat, lng = loc.latitude, loc.longitude
            loc_name = loc.name
            
        success_msg = f"🔓 ปลดล็อคกลุ่มฝน (Auto-track) ของ {loc_name.capitalize()} เรียบร้อยแล้ว"
        await _reply(chat_id, success_msg, message_id_to_edit)
        await process_telegram_location(chat_id, lat, lng, location_name=loc_name, is_lock_command=True)
    except Exception as e:
        logger.error(f"Error handling unlock command: {e}")
        await _reply(chat_id, f"❌ เกิดข้อผิดพลาด: {str(e)}", message_id_to_edit)


@cmd_router.bind("/mylocation", task_route="worker/handle-mylocation")
async def handle_mylocation_command(chat_id: int):
    async with get_repo_context() as repo:
        locs = await repo.get_user_locations(chat_id)

    if not locs:
        text = "คุณยังไม่ได้บันทึกตำแหน่งใดๆ ไว้ในระบบ"
        reply_markup = None
    else:
        text = "📍 พิกัดที่บันทึกไว้ของคุณ:\n\n"
        keyboard = []
        for loc in locs:
            expires = "จำตลอดไป"
            if loc.expires_at:
                expires = loc.expires_at.strftime("%Y-%m-%d %H:%M:%S UTC")

            loc_name = loc.name if loc.name else "default"

            icon = "📍"
            if loc_name.lower() == "home":
                icon = "🏠"
            elif loc_name.lower() == "work":
                icon = "💼"

            text += f"{icon} {loc_name.capitalize()}: {loc.latitude}, {loc.longitude}\n"
            text += f"⏳ วันหมดอายุ: {expires}\n\n"

            keyboard.append([{"text": f"🗑️ ลบ {loc_name.capitalize()}", "callback_data": f"loc_del_{loc_name.lower()}"}])

        text += "หากต้องการเปลี่ยนแปลงพิกัด ให้ส่ง Location ใหม่อีกครั้ง หรือกดปุ่มด้านล่างเพื่อลบข้อมูล"

        reply_markup = {
            "inline_keyboard": keyboard
        }

    await telegram.send_telegram_message(chat_id, text, reply_markup)


@cmd_router.bind("/radar", task_route="worker/handle-radar")
async def handle_radar_command(chat_id: int):
    async with get_repo_context() as repo:
        loc = await repo.get_location(chat_id)

    if not loc:
        text = "คุณยังไม่ได้บันทึกตำแหน่งใดๆ ไว้ในระบบ กรุณาส่งพิกัด Location ของคุณให้บอทก่อนครับ 📍"
        await telegram.send_telegram_message(chat_id, text)
    else:
        text = "📡 คุณสามารถเช็คเรดาร์ฝนด้วยตัวเองได้จากแหล่งข้อมูลเหล่านี้:"
        is_dev = str(chat_id) in telegram.DEVELOPER_CHAT_IDS
        reply_markup = telegram.get_radar_inline_keyboard(loc.latitude, loc.longitude, is_developer=is_dev)
        await telegram.send_telegram_message(chat_id, text, reply_markup=reply_markup)


@cmd_router.bind("/rain_pro", requires_admin=True, task_route="worker/handle-rain", loading_text="⏳ กำลังประมวลผล...", show_advanced=True)
@cmd_router.bind("/rain", requires_admin=True, task_route="worker/handle-rain", loading_text="⏳ กำลังประมวลผล...")
@cmd_router.bind("/check", requires_admin=True, task_route="worker/handle-rain", loading_text="⏳ กำลังประมวลผล...", command_override="/rain tmd-radar")
async def handle_rain_command(chat_id: int, command: str, show_advanced: bool = False, message_id_to_edit: int = None):
    import re
    coords_match = re.search(r'([+-]?\d+\.\d+)[,\s]+([+-]?\d+\.\d+)', command)
    custom_lat = None
    custom_lng = None
    if coords_match:
        try:
            custom_lat = float(coords_match.group(1))
            custom_lng = float(coords_match.group(2))
            command = command.replace(coords_match.group(0), "").strip()
        except ValueError:
            pass

    parts = command.strip().split()
    force_provider = None
    target_location_name = None
    
    known_providers = ["tmd-radar", "tomorrow", "rainbow-local", "rainbow-global", "xweather", "open-meteo", "tmd", "kkn120", "kkn240", "skn240"]
    provider_aliases = {"tmd": "tmd-radar"}
    
    if len(parts) > 1:
        part1 = parts[1].lower()
        if part1 in known_providers:
            force_provider = part1
            if len(parts) > 2:
                target_location_name = parts[2].lower()
        else:
            target_location_name = part1
            if len(parts) > 2 and parts[2].lower() in known_providers:
                force_provider = parts[2].lower()
                
    if force_provider in provider_aliases:
        force_provider = provider_aliases[force_provider]
    
    loc = None
    if custom_lat is not None and custom_lng is not None:
        from app.models import UserLocation
        loc = UserLocation(
            chat_id=chat_id,
            latitude=custom_lat,
            longitude=custom_lng,
            name=f"{custom_lat}, {custom_lng}"
        )
    else:
        async with get_repo_context() as repo:
            locs = await repo.get_user_locations(chat_id)
            
        if not locs:
            await telegram.send_telegram_message(chat_id, "⚠️ ไม่พบพิกัดที่บันทึกไว้ กรุณาส่ง Location ให้บอทก่อนครับ")
            return
            
        if target_location_name == "all":
            if message_id_to_edit:
                await telegram.edit_telegram_message(chat_id, message_id_to_edit, f"⏳ กำลังตรวจสอบสภาพอากาศทั้งหมด {len(locs)} จุด...")
            else:
                await telegram.send_telegram_message(chat_id, f"⏳ กำลังตรวจสอบสภาพอากาศทั้งหมด {len(locs)} จุด...")
            for l in locs:
                loc_display = l.name.capitalize() if l.name else "Default"
                msg_text = f"⏳ กำลังตรวจสอบสภาพอากาศที่ '{loc_display}'..."
                loading_msg_id = await telegram.send_telegram_message_return_id(chat_id, msg_text)
                await process_telegram_location(
                    chat_id, lat=l.latitude, lng=l.longitude,
                    force_endpoint=force_provider, message_id_to_edit=loading_msg_id,
                    show_advanced=show_advanced, location_name=loc_display
                )
            return

        if target_location_name:
            if target_location_name != "default" and chat_id in LAST_PINNED_LOCATION:
                LAST_PINNED_LOCATION.pop(chat_id, None)
            for l in locs:
                if (l.name and l.name.lower() == target_location_name) or (target_location_name == "default" and l.name is None):
                    loc = l
                    break
            if not loc:
                available_locs = ", ".join([l.name for l in locs if l.name])
                await telegram.send_telegram_message(chat_id, f"⚠️ ไม่พบพิกัดชื่อ '{target_location_name}'\nพิกัดที่มี: {available_locs or 'default'}")
                return
        else:
            loc = locs[0]
        
    loc_display = loc.name.capitalize() if loc.name else "ระบบอัตโนมัติ"
    msg_text = f"⏳ กำลังตรวจสอบสภาพอากาศที่ '{loc_display}' "
    if force_provider:
        msg_text += f"จาก {force_provider}..."
    else:
        msg_text += "..."
        
    loading_msg_id = await telegram.send_telegram_message_return_id(chat_id, msg_text)
    
    await process_telegram_location(
        chat_id, lat=loc.latitude, lng=loc.longitude,
        force_endpoint=force_provider, message_id_to_edit=loading_msg_id,
        show_advanced=show_advanced, location_name=loc_display
    )
