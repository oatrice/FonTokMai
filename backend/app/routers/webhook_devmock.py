from app.services.command_router import router as cmd_router
from .webhook_utils import (
    log_audit_event, check_admin_access, get_repo_context, logger
)
from app.services import telegram
from .webhook_location import process_telegram_location
import re
import json
import time
from datetime import datetime, timezone
import cv2
import asyncio

@cmd_router.bind("/tmd_fallback", requires_admin=True, audit_log=True, task_route="worker/handle-tmd-fallback", loading_text="⏳ กำลังสลับระบบข้อมูล...")
async def handle_tmd_fallback_command(chat_id: int, command: str, username: str = "", message_id_to_edit: int = None):
    """
    /tmd_fallback on
    /tmd_fallback off
    """
    if not await check_admin_access(chat_id):
        return

    parts = command.strip().split()
    if len(parts) < 2:
        async with get_repo_context() as repo:
            sys_settings = await repo.get_system_settings()
            current_status = sys_settings.get("enable_gif_fallback", True)
            
        status_str = "ON 🟢" if current_status else "OFF 🔴"
        await telegram.send_telegram_message(
            chat_id,
            f"ℹ️ สถานะ GIF Fallback ปัจจุบัน: {status_str}\n"
            "พิมพ์ `/tmd_fallback on` หรือ `/tmd_fallback off` เพื่อเปลี่ยน"
        )
        return

    action = parts[1].lower()
    enable = True if action == "on" else False

    async with get_repo_context() as repo:
        sys_settings = await repo.get_system_settings()
        sys_settings["enable_gif_fallback"] = enable
        await repo.set_system_settings(sys_settings)

    status_str = "ON 🟢" if enable else "OFF 🔴"
    await telegram.send_telegram_message(
        chat_id,
        f"✅ ตั้งค่า GIF Fallback เป็น {status_str} เรียบร้อยแล้ว"
    )


@cmd_router.bind("/devmock", requires_admin=True, audit_log=True, task_route="worker/handle-devmock", loading_text="⏳ กำลังเข้าสู่ DevMock Mode...")
async def handle_devmock_command(chat_id: int, command: str, username: str = "", message_id_to_edit: int = None):
    if not await check_admin_access(chat_id):
        return

    async with get_repo_context() as repo:
        if command == "/devmock rain":
            await repo.set_mock_state(chat_id, "rain")

            # Reset cooldown สำหรับทุก location ของ user นี้ เพื่อให้ alert ยิงทันที
            locs = await repo.get_user_locations(chat_id)
            for loc in locs:
                await repo.update_last_alerted(loc, None)

            if message_id_to_edit: await telegram.edit_telegram_message(chat_id, message_id_to_edit, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: 🌧️ ฝนตกหนัก (Boost เมฆจริง)\n⏳ กำลังสร้างแจ้งเตือน...")
            else: await telegram.send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: 🌧️ ฝนตกหนัก (Boost เมฆจริง)\n⏳ กำลังสร้างแจ้งเตือน...")

            from app.scheduler_tasks import check_rain_and_alert
            await check_rain_and_alert()
            
        elif command == "/devmock storm":
            await repo.set_mock_state(chat_id, "storm")

            # Reset cooldown สำหรับทุก location ของ user นี้ เพื่อให้ alert ยิงทันที
            locs = await repo.get_user_locations(chat_id)
            for loc in locs:
                await repo.update_last_alerted(loc, None)

            if message_id_to_edit: await telegram.edit_telegram_message(chat_id, message_id_to_edit, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: 🌪️ พายุจำลอง (สร้างเมฆปลอม 5 สี)\n⏳ กำลังสร้างแจ้งเตือน...")
            else: await telegram.send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: 🌪️ พายุจำลอง (สร้างเมฆปลอม 5 สี)\n⏳ กำลังสร้างแจ้งเตือน...")

            from app.scheduler_tasks import check_rain_and_alert
            await check_rain_and_alert()
            
        elif command == "/devmock clear":
            await repo.set_mock_state(chat_id, "clear")
            if message_id_to_edit: await telegram.edit_telegram_message(chat_id, message_id_to_edit, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: ☀️ ท้องฟ้าแจ่มใส\n⏳ กำลังตรวจสอบสภาพอากาศ...")
            else: await telegram.send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: ☀️ ท้องฟ้าแจ่มใส\n⏳ กำลังตรวจสอบสภาพอากาศ...")
            
            from app.scheduler_tasks import check_rain_and_alert
            await check_rain_and_alert()
            
        elif command == "/devmock error":
            await repo.set_mock_state(chat_id, "error")
            if message_id_to_edit: await telegram.edit_telegram_message(chat_id, message_id_to_edit, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: ❌ เชื่อมต่อ API ล้มเหลวทั้งหมด\n⏳ กำลังส่งตำแหน่งเพื่อทดสอบ Fallback...")
            else: await telegram.send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: ❌ เชื่อมต่อ API ล้มเหลวทั้งหมด\n⏳ กำลังส่งตำแหน่งเพื่อทดสอบ Fallback...")
            
            # Simulate a location update to trigger the fallback error message immediately
            locs = await repo.get_user_locations(chat_id)
            if locs:
                await process_telegram_location(chat_id, locs[0].latitude, locs[0].longitude, message_id_to_edit=None)
            else:
                if message_id_to_edit: await telegram.edit_telegram_message(chat_id, message_id_to_edit, "ไม่พบตำแหน่งที่บันทึกไว้ โปรดส่ง Location มาใหม่เพื่อทดสอบ error")
                else: await telegram.send_telegram_message(chat_id, "ไม่พบตำแหน่งที่บันทึกไว้ โปรดส่ง Location มาใหม่เพื่อทดสอบ error")

        elif command.startswith("/devmock scenario"):
            import json as _json
            from app.services.weather_manager import _parse_scenario_params

            params_str = command.removeprefix("/devmock scenario").strip()
            if not params_str:
                await telegram.send_telegram_message(
                    chat_id,
                    "🛠️ [DEV MOCK] ต้องระบุพารามิเตอร์ เช่น:\n"
                    "/devmock scenario rain_in:20 dbz:40 wind:60 wind_dir:N\n"
                    "พิมพ์ /devmock help เพื่อดูตัวเลือกทั้งหมด"
                )
                return

            scenario = _parse_scenario_params(params_str)

            # Extract optional loc:name parameter (not a scenario param)
            target_loc_name = scenario.pop("loc", None)
            if target_loc_name:
                target_loc_name = str(target_loc_name).lower()

            mock_state_json = _json.dumps(scenario, ensure_ascii=False)
            await repo.set_mock_state(chat_id, mock_state_json)

            # Reset cooldown — only for the target location (or all if not specified)
            locs = await repo.get_user_locations(chat_id)

            if target_loc_name:
                matched = [l for l in locs if l.name and l.name.lower() == target_loc_name]
                if not matched:
                    available = ", ".join([l.name for l in locs if l.name]) or "default"
                    await telegram.send_telegram_message(
                        chat_id,
                        f"⚠️ ไม่พบพิกัดชื่อ '{target_loc_name}'\nพิกัดที่มี: {available}"
                    )
                    return
                fire_locs = matched
            else:
                fire_locs = locs

            for loc in fire_locs:
                await repo.update_last_alerted(loc, None)

            # Build a human-readable summary of the scenario
            parts = []
            if target_loc_name:
                parts.append(f"📍 พิกัด: {target_loc_name.capitalize()}")
            if "rain_in" in scenario:
                parts.append(f"🕐 ฝนจะมาใน {scenario['rain_in']} นาที")
            if "rain_stopping" in scenario:
                parts.append(f"🌤 ฝนจะหยุดใน {scenario['rain_stopping']} นาที")
            if scenario.get("no_rain"):
                parts.append("☀️ ไม่มีฝน")
            if "dbz" in scenario:
                parts.append(f"📡 dBZ: {scenario['dbz']}")
            if "wind" in scenario:
                wind_dir = scenario.get("wind_dir", "?")
                parts.append(f"💨 ลม: {scenario['wind']} km/h จากทิศ {wind_dir}")
            if "growth" in scenario:
                sign = "+" if float(scenario["growth"]) >= 0 else ""
                parts.append(f"📈 Growth: {sign}{scenario['growth']}")
            if "clusters" in scenario:
                parts.append(f"☁️ เมฆ: {scenario['clusters']} ก้อน")

            summary = "\n".join(parts) if parts else "(ไม่มีพารามิเตอร์พิเศษ)"
            await telegram.send_telegram_message(
                chat_id,
                f"🛠️ [DEV MOCK] Scenario จำลอง:\n{summary}\n\n⏳ กำลังสร้างแจ้งเตือน..."
            )

            from app.scheduler_tasks import check_rain_and_alert, run_alert_for_locations
            if target_loc_name:
                await run_alert_for_locations(fire_locs)
            else:
                await check_rain_and_alert()

        elif command in ("/devmock help", "/devmock"):
            help_text = (
                "🛠️ <b>DEV MOCK — คำสั่งทั้งหมด</b>\n\n"
                "<b>โหมดพื้นฐาน:</b>\n"
                "<code>/devmock rain</code> — ฝนตกหนัก (Boost เมฆจริง)\n"
                "<code>/devmock storm</code> — พายุจำลอง 5 ก้อนเมฆ\n"
                "<code>/devmock clear</code> — ท้องฟ้าแจ่มใส\n"
                "<code>/devmock error</code> — API ล้มเหลวทั้งหมด\n"
                "<code>/devmock off</code> — ปิด mock mode\n\n"
                "<b>โหมด Parametric Scenario:</b>\n"
                "<code>/devmock scenario &lt;params&gt;</code>\n\n"
                "<b>พารามิเตอร์ที่รองรับ:</b>\n"
                "<code>rain_in:N</code> — ฝนจะมาใน N นาที\n"
                "<code>rain_stopping:N</code> — ฝนจะหยุดใน N นาที\n"
                "<code>no_rain</code> — ไม่มีฝน (ทดสอบลมอย่างเดียว)\n"
                "<code>dbz:N</code> — ความเข้มฝน dBZ (15–75, default 35)\n"
                "<code>wind:N</code> — ความเร็วลม km/h (default 20)\n"
                "<code>wind_dir:X</code> — ทิศลม: N/NE/E/SE/S/SW/W/NW\n"
                "<code>growth:N</code> — อัตราการเติบโต ±0.0–1.0\n"
                "<code>clusters:N</code> — จำนวนก้อนเมฆ 1–5 (default 1)\n"
                "<code>loc:NAME</code> — เจาะจงพิกัด (เช่น home, work)\n\n"
                "<b>ตัวอย่าง:</b>\n"
                "<code>/devmock scenario rain_in:20 dbz:40 wind:60 wind_dir:N</code>\n"
                "<code>/devmock scenario rain_in:10 dbz:55 growth:0.3 loc:work</code>\n"
                "<code>/devmock scenario rain_stopping:10 dbz:30 loc:home</code>\n"
                "<code>/devmock scenario no_rain wind:45 wind_dir:SE loc:home</code>\n\n"
                "<b>Dev/Test:</b>\n"
                "<code>/devmock check lat,lng</code> — เช็คฝน ณ พิกัดใดก็ได้\n"
                "<code>/devmock pixel lat,lng</code> — GPS → pixel (ทุก station)\n"
                "<code>/devmock pixel px,py skn240</code> — pixel → GPS\n"
                "<code>/devmock config</code> — ดู/ปรับ thresholds (cluster_min, min_dbz ฯลฯ)\n"
                "<code>/devmock flush_cache</code> — ล้าง in-memory cache (บังคับ GIF fallback)\n"
                "<code>/devmock flush_all_cache</code> — ล้าง in-memory + Firestore (GIF fallback ทันที)\n"
                "<code>/devmock cache_status</code> — ดูสถานะ cache ทุก layer"
            )
            await telegram.send_telegram_message(chat_id, help_text, parse_mode="HTML")


        elif command == "/devmock off":
            await repo.set_mock_state(chat_id, None)
            await telegram.send_telegram_message(chat_id, "🛠️ [DEV MOCK] ปิดใช้งานโหมดจำลองเรียบร้อยแล้ว\n⏳ กำลังส่งสถานะ All-Clear...")
            
            from app.scheduler_tasks import check_rain_and_alert
            await check_rain_and_alert()

        elif command == "/devmock flush_cache":
            from app.services.weather_manager import _GLOBAL_TMD_CACHE, _GLOBAL_TMD_LOCKS
            stations_cleared = list(_GLOBAL_TMD_CACHE.keys())
            _GLOBAL_TMD_CACHE.clear()
            stations_str = ", ".join(f"<code>{s}</code>" for s in stations_cleared) if stations_cleared else "<i>(ว่างอยู่แล้ว)</i>"
            msg = (
                "🗑️ <b>In-memory TMD cache cleared</b>\n\n"
                f"สถานีที่ล้าง: {stations_str}\n\n"
                "👉 ยิง <code>/devmock scenario ...</code> ต่อเพื่อทดสอบ GIF fallback\n"
                "<i>(ระบบจะโหลดจาก Firestore หรือ loop GIF แทน in-memory)</i>"
            )
            await telegram.send_telegram_message(chat_id, msg, parse_mode="HTML")

        elif command == "/devmock flush_all_cache":
            from app.services.weather_manager import _GLOBAL_TMD_CACHE
            _STATIONS = ["kkn240", "skn240", "kkn120"]

            # 1) Clear in-memory
            mem_before = list(_GLOBAL_TMD_CACHE.keys())
            _GLOBAL_TMD_CACHE.clear()

            # 2) Clear Firestore radar_latest_cache
            fs_cleared, fs_failed = [], []
            async with get_repo_context() as _repo:
                for st in _STATIONS:
                    try:
                        doc_ref = _repo.db.collection("radar_latest_cache").document(st)
                        await doc_ref.delete()
                        fs_cleared.append(st)
                    except Exception as _e:
                        fs_failed.append(f"{st}({_e})")

            mem_str = ", ".join(f"<code>{s}</code>" for s in mem_before) if mem_before else "<i>(ว่างอยู่แล้ว)</i>"
            fs_str  = ", ".join(f"<code>{s}</code>" for s in fs_cleared)
            fail_str = (f"\n⚠️ ล้มเหลว: {', '.join(fs_failed)}" if fs_failed else "")
            msg = (
                "🗑️ <b>Full cache cleared</b>\n\n"
                f"📦 In-Memory: {mem_str}\n"
                f"🗃️ Firestore: {fs_str}{fail_str}\n\n"
                "⚡ Cache phase รอบถัดไป (~20s) จะ bootstrap 6 frames อัตโนมัติ\n"
                "<i>(static frame ล่าสุด + GIF history → Firestore พร้อมใช้ทันที)</i>"
            )
            await telegram.send_telegram_message(chat_id, msg, parse_mode="HTML")


        elif command == "/devmock cache_status":
            from app.services.weather_manager import _GLOBAL_TMD_CACHE
            import time as _time
            from zoneinfo import ZoneInfo as _ZI
            _bkk = _ZI("Asia/Bangkok")


            lines = ["🗂️ <b>TMD Cache Status</b>\n"]

            # ── Layer 1: In-memory ─────────────────────────────
            lines.append("<b>📦 In-Memory (_GLOBAL_TMD_CACHE)</b>")
            if not _GLOBAL_TMD_CACHE:
                lines.append("  <i>(ว่าง)</i>")
            else:
                for st, entry in _GLOBAL_TMD_CACHE.items():
                    n_frames  = len(entry[0]) if entry[0] else 0
                    cached_at = entry[2]
                    src       = entry[4] if len(entry) > 4 else "?"
                    ts_list   = list(entry[6]) if len(entry) > 6 else []
                    age_s     = int(_time.time() - cached_at)
                    ttl_left  = max(0, 600 - age_s)
                    latest_bkk = (
                        __import__("datetime").datetime.fromtimestamp(ts_list[-1], _bkk).strftime("%H:%M")
                        if ts_list else "?"
                    )
                    lines.append(
                        f"  <code>{st}</code> {n_frames}f  src=<code>{src}</code>"
                        f"  latest={latest_bkk} BKK  age={age_s}s  TTL={ttl_left}s"
                    )

            # ── Layer 2: Firestore station cache ───────────────
            lines.append("\n<b>🗃️ Firestore (radar_latest_cache)</b>")
            async with get_repo_context() as _repo:
                for st in ["kkn240", "skn240", "kkn120"]:
                    c = await _repo.get_latest_radar_cache(st)
                    if c and c.get("frames"):
                        fs = sorted(c["frames"], key=lambda x: x["timestamp"])
                        latest_bkk = (
                            __import__("datetime").datetime.fromtimestamp(fs[-1]["timestamp"], _bkk).strftime("%H:%M")
                        )
                        lines.append(f"  <code>{st}</code> {len(fs)}f  latest={latest_bkk} BKK")
                    else:
                        lines.append(f"  <code>{st}</code> <i>(ว่าง)</i>")

            await telegram.send_telegram_message(chat_id, "\n".join(lines), parse_mode="HTML")

        # ── /devmock check lat,lng ─────────────────────────────────────────────
        elif command.startswith("/devmock check"):
            import re as _re
            args = command.removeprefix("/devmock check").strip()
            coords_m = _re.search(r'([+-]?\d+\.?\d*)[,\s]+([+-]?\d+\.?\d*)', args)
            if not coords_m:
                await telegram.send_telegram_message(
                    chat_id,
                    "🛠️ ใช้: <code>/devmock check lat,lng</code>\n"
                    "เช่น: <code>/devmock check 18.665,101.861</code>",
                    parse_mode="HTML",
                )
                return
            chk_lat = float(coords_m.group(1))
            chk_lng = float(coords_m.group(2))
            await telegram.send_telegram_message(
                chat_id,
                f"🛠️ กำลังเช็คฝน ณ พิกัด <code>{chk_lat:.5f}, {chk_lng:.5f}</code>…",
                parse_mode="HTML",
            )
            await process_telegram_location(chat_id, chk_lat, chk_lng, message_id_to_edit=None)

        # ── /devmock pixel lat,lng  or  /devmock pixel px,py station ──────────
        elif command.startswith("/devmock pixel"):
            import re as _re
            from app.services.tmd_radar_config import STATIONS
            from app.services.tmd_radar_processor import TMDRadarProcessor as _TRP
            args = command.removeprefix("/devmock pixel").strip()
            # Detect mode: if values have '.', treat as lat/lng; else as pixel coords
            nums = _re.findall(r'[+-]?\d+\.?\d*', args)
            station_hint = _re.search(r'(kkn\d+|skn\d+)', args.lower())
            st_code = station_hint.group(1) if station_hint else None

            if len(nums) < 2:
                await telegram.send_telegram_message(
                    chat_id,
                    "🛠️ ใช้:\n"
                    "<code>/devmock pixel lat,lng</code> — แปลง GPS → pixel\n"
                    "<code>/devmock pixel px,py station</code> — แปลง pixel → GPS\n"
                    "เช่น: <code>/devmock pixel 18.665,101.861</code>\n"
                    "เช่น: <code>/devmock pixel 300,200 skn240</code>",
                    parse_mode="HTML",
                )
                return

            is_latlng = '.' in nums[0] or '.' in nums[1]
            lines_px = [f"🗺️ <b>Pixel Coordinate Tool</b>\n"]
            if is_latlng:
                lat_v = float(nums[0])
                lng_v = float(nums[1])
                lines_px.append(f"📍 GPS: <code>{lat_v:.5f}, {lng_v:.5f}</code>\n")
                for sc, cfg in STATIONS.items():
                    try:
                        proc = _TRP(sc)
                        px_loop, py_loop = proc.latlng_to_pixel(lat_v, lng_v, is_loop=True)
                        px_stat, py_stat = proc.latlng_to_pixel(lat_v, lng_v, is_loop=False)
                        if px_loop is None:
                            lines_px.append(f"  <code>{sc}</code>: นอก bbox")
                            continue
                        lines_px.append(
                            f"  <code>{sc}</code>: loop=<code>({px_loop},{py_loop})</code>  static=<code>({px_stat},{py_stat})</code>"
                        )
                    except Exception:
                        pass
            else:
                # Pixel → lat/lng
                px_v = int(float(nums[0]))
                py_v = int(float(nums[1]))
                target_st = st_code or "skn240"
                lines_px.append(f"📍 Pixel: <code>({px_v}, {py_v})</code>  station=<code>{target_st}</code>\n")
                try:
                    proc = _TRP(target_st)
                    cfg = proc.config
                    bbox = cfg.bbox
                    # Reverse loop mapping
                    cw, ch = cfg.loop_crop_width, cfg.loop_crop_height
                    x_pct = (px_v - cfg.loop_crop_x) / cw
                    y_pct = (py_v - cfg.loop_crop_y) / ch
                    lng_v = x_pct * (bbox.lng_max - bbox.lng_min) + bbox.lng_min
                    lat_v = bbox.lat_max - y_pct * (bbox.lat_max - bbox.lat_min)
                    lines_px.append(f"  → GPS (loop): <code>{lat_v:.5f}, {lng_v:.5f}</code>")
                    # Also show reverse for static
                    cw2, ch2 = cfg.static_crop_width, cfg.static_crop_height
                    x_pct2 = (px_v - cfg.static_crop_x) / cw2
                    y_pct2 = (py_v - cfg.static_crop_y) / ch2
                    lng_v2 = x_pct2 * (bbox.lng_max - bbox.lng_min) + bbox.lng_min
                    lat_v2 = bbox.lat_max - y_pct2 * (bbox.lat_max - bbox.lat_min)
                    lines_px.append(f"  → GPS (static): <code>{lat_v2:.5f}, {lng_v2:.5f}</code>")
                except Exception as _e:
                    lines_px.append(f"  ❌ Error: {_e}")
            await telegram.send_telegram_message(chat_id, "\n".join(lines_px), parse_mode="HTML")

        # ── /devmock config [key:val ...] ──────────────────────────────────────
        elif command.startswith("/devmock config"):
            from app.services.weather_manager import _DEV_CONFIG
            args = command.removeprefix("/devmock config").strip()
            if not args:
                # Show current config
                lines_cfg = ["🛠️ <b>Dev Config (ค่าปัจจุบัน)</b>\n"]
                for k, v in _DEV_CONFIG.items():
                    lines_cfg.append(f"  <code>{k}</code> = <b>{v}</b>")
                lines_cfg.append(
                    "\n<b>ปรับได้:</b>\n"
                    "<code>/devmock config cluster_min:1</code>\n"
                    "<code>/devmock config search_radius:120</code>\n"
                    "<code>/devmock config min_dbz:5</code>\n"
                    "<code>/devmock config dot_threshold:0.3</code>\n"
                    "<code>/devmock config flow_mode:average</code>\n"
                    "<code>/devmock config decay_enabled:false</code>\n"
                    "<code>/devmock config prediction_steps:10</code>\n"
                    "<code>/devmock config reset</code> — คืนค่า default"
                )
                await telegram.send_telegram_message(chat_id, "\n".join(lines_cfg), parse_mode="HTML")
                return

            if args.strip() == "reset":
                _DEV_CONFIG["cluster_min"]   = 3
                _DEV_CONFIG["search_radius"] = 80
                _DEV_CONFIG["min_dbz"]       = 10.0
                _DEV_CONFIG["dot_threshold"] = 0.5
                _DEV_CONFIG["flow_mode"]     = "average"
                _DEV_CONFIG["hit_radius"]    = 8
                _DEV_CONFIG["verbose"]       = False
                _DEV_CONFIG["draw_debug_grid"] = False
                _DEV_CONFIG["decay_enabled"] = True
                _DEV_CONFIG["prediction_steps"] = 7
                _DEV_CONFIG["enable_raster_smooth"] = True
                _DEV_CONFIG["gaussian_kernel_size"] = 15
                _DEV_CONFIG["raster_smooth_threshold"] = 80
                _DEV_CONFIG["draw_all_ambient_polygons"] = False
                _DEV_CONFIG["enable_hsv_mask"] = False
                await repo.set_global_dev_config(_DEV_CONFIG)
                await telegram.send_telegram_message(chat_id, "🛠️ Dev Config รีเซ็ตเป็นค่า default แล้วครับ ✅")
                return

            import re as _re
            changed = []
            
            # Supported new settings keys with their default type mappings for auto-registration
            dynamic_defaults = {
                "enable_raster_smooth": True,
                "gaussian_kernel_size": 15,
                "raster_smooth_threshold": 80,
                "draw_all_ambient_polygons": False,
                "enable_hsv_mask": False,
                "draw_debug_grid": False
            }
            
            for pair in _re.findall(r'(\w+)\s*:\s*([a-zA-Z0-9_.-]+)', args):
                key, raw_val = pair
                if key not in _DEV_CONFIG:
                    if key in dynamic_defaults:
                        # Dynamically register key with fallback type structure
                        _DEV_CONFIG[key] = dynamic_defaults[key]
                    else:
                        continue
                try:
                    cur = _DEV_CONFIG[key]
                    if isinstance(cur, bool):
                        new_val = raw_val.lower() in ("true", "1", "yes")
                    elif isinstance(cur, (int, float)):
                        new_val = type(cur)(raw_val)
                    else:
                        new_val = raw_val
                    _DEV_CONFIG[key] = new_val
                    changed.append(f"  <code>{key}</code>: {cur} → <b>{new_val}</b>")
                except Exception:
                    pass
            if changed:
                await repo.set_global_dev_config(_DEV_CONFIG)
                await telegram.send_telegram_message(
                    chat_id,
                    "🛠️ <b>Dev Config อัพเดต</b>\n" + "\n".join(changed),
                    parse_mode="HTML",
                )
            else:
                await telegram.send_telegram_message(
                    chat_id,
                    "⚠️ ไม่พบ key ที่รู้จัก\nKey ที่รองรับ: <code>" + ", ".join(_DEV_CONFIG.keys()) + "</code>",
                    parse_mode="HTML",
                )

        # ── /devmock cleancache [station] ──────────────────────────────────────
        elif command.startswith("/devmock cleancache"):
            args = command.removeprefix("/devmock cleancache").strip()
            station = args if args else "skn240"
            
            from app.services.weather_manager import _GLOBAL_TMD_CACHE
            _GLOBAL_TMD_CACHE.pop(station, None)
            await repo.set_latest_radar_cache(station, [])
            
            await telegram.send_telegram_message(chat_id, f"🔄 ล้าง Cache ของสถานี {station} สำเร็จ!\nการเช็คฝนรอบถัดไปจะดึงภาพใหม่ล่าสุดจาก TMD ครับ")

        # ── /devmock fetch_latest [station] ────────────────────────────────────
        elif command.startswith("/devmock fetch_latest"):
            args = command.removeprefix("/devmock fetch_latest").strip()
            station = args if args else "skn240"
            
            await telegram.send_telegram_message(chat_id, f"🔄 กำลังเช็คภาพล่าสุดแบบเดี่ยวของสถานี {station}...")
            
            from app.services.weather_manager import _GLOBAL_TMD_CACHE, _DEV_CONFIG
            from app.services.tmd_radar_processor import TMDRadarProcessor
            from app.services.ocr_service import OCRService
            import time
            from datetime import datetime, timezone
            import cv2
            
            cached_data = _GLOBAL_TMD_CACHE.get(station)
            if not cached_data or not cached_data[0]:
                from app.services import weather_manager
                wm = weather_manager.WeatherManager()
                processor = TMDRadarProcessor(station)
                cached_data = await wm.load_persistent_cache_to_memory(station, processor)
                
            if not cached_data or not cached_data[0]:
                await telegram.send_telegram_message(chat_id, f"❌ ไม่มี Cache เก่าสำหรับ {station} (ในฐานข้อมูลก็ไม่มีเช่นกัน ต้องใช้ /rain ก่อนครับ)")
                return
                
            frames = list(cached_data[0])
            frame_timestamps = list(cached_data[6]) if len(cached_data) > 6 else []
            
            if not frame_timestamps:
                await telegram.send_telegram_message(chat_id, f"❌ ไม่มีข้อมูล Timestamp ใน Cache ของ {station}")
                return
                
            processor = TMDRadarProcessor(station)
            new_frame = await processor.decode_static_frame()
            if new_frame is None:
                await telegram.send_telegram_message(chat_id, f"❌ โหลดภาพล่าสุด (Static) จาก TMD ไม่สำเร็จ")
                return
                
            target_h, target_w = frames[-1].shape[:2]
            if new_frame.shape[:2] != (target_h, target_w):
                new_frame = cv2.resize(new_frame, (target_w, target_h), interpolation=cv2.INTER_NEAREST)
                
            ocr_svc = OCRService()
            new_ts = await ocr_svc.get_frame_timestamp(new_frame, fallback_ts=int(time.time()))
            
            if new_ts is None:
                await telegram.send_telegram_message(chat_id, f"❌ อ่านเวลาจากภาพใหม่ไม่สำเร็จ")
                return
                
            # Check if the retrieved static image is outdated (older than 2 hours)
            now_ts = time.time()
            static_age_minutes = (now_ts - new_ts) / 60.0
            if static_age_minutes > 120.0:
                await telegram.send_telegram_message(
                    chat_id, 
                    f"⚠️ ตรวจพบภาพนิ่ง (Static) ล้าหลังเกิน 2 ชั่วโมง ({static_age_minutes:.0f} นาที) ทำการล้าง Cache เพื่อบังคับดึง Loop GIF ใหม่ครับ"
                )
                _GLOBAL_TMD_CACHE.pop(station, None)
                async with get_repo_context() as repo:
                    await repo.set_latest_radar_cache(station, [])
                return
                
            if new_ts <= frame_timestamps[-1]:
                await telegram.send_telegram_message(chat_id, f"⚠️ ภาพล่าสุดในเว็บ ({datetime.fromtimestamp(new_ts).strftime('%H:%M')}) ยังไม่ใหม่กว่าที่เรามีอยู่ ({datetime.fromtimestamp(frame_timestamps[-1]).strftime('%H:%M')})")
                return
                
            gap_minutes = (new_ts - frame_timestamps[-1]) / 60.0
            if gap_minutes > 30.0:
                await telegram.send_telegram_message(chat_id, f"⚠️ ภาพใหม่ห่างจากภาพเดิมเกิน 30 นาที ({gap_minutes:.0f} นาที) ทำการล้าง Cache เพื่อบังคับดึง Loop GIF ใหม่ครับ")
                _GLOBAL_TMD_CACHE.pop(station, None)
                async with get_repo_context() as repo:
                    await repo.set_latest_radar_cache(station, [])
                return
                
            # Append new frame
            frames.append(new_frame)
            frame_timestamps.append(new_ts)
            
            if len(frames) > 6:
                frames = frames[-6:]
                frame_timestamps = frame_timestamps[-6:]
                
            if _DEV_CONFIG.get("flow_mode", "latest") == "average":
                flow = processor.calculate_average_optical_flow(frames)
            else:
                flow = processor.calculate_optical_flow(frames)
                
            data_gap_minutes = (frame_timestamps[-1] - frame_timestamps[-2]) / 60.0
            new_dt = datetime.fromtimestamp(new_ts, timezone.utc)
            
            _GLOBAL_TMD_CACHE[station] = (
                frames, new_dt, time.time(), flow,
                "static_append", data_gap_minutes, frame_timestamps
            )
            
            # Persist to DB
            saved_frames = []
            for f_img, f_ts in zip(frames, frame_timestamps):
                if f_img.shape[0] != 800 or f_img.shape[1] != 800:
                    f_img_r = cv2.resize(f_img, (800, 800), interpolation=cv2.INTER_NEAREST)
                else:
                    f_img_r = f_img
                is_ok, buf = cv2.imencode(".png", cv2.cvtColor(f_img_r, cv2.COLOR_RGB2BGR))
                if is_ok:
                    f_url = await processor.save_polled_frame(buf.tobytes())
                    saved_frames.append({"url": f_url, "timestamp": f_ts})
            
            if saved_frames:
                await repo.set_latest_radar_cache(station_code=station, frames=saved_frames)
                
                await telegram.send_telegram_message(chat_id, f"✅ ต่อภาพล่าสุด ({new_dt.strftime('%H:%M')}) สำเร็จ! อัพเดต Cache และ Optical Flow เรียบร้อยครับ")

        # ── /devmock visualize_flow [station] ──────────────────────────────────
        elif command.startswith("/devmock visualize_flow"):
            args = command.removeprefix("/devmock visualize_flow").strip()
            station = args if args else "skn240"
            await telegram.send_telegram_message(
                chat_id, 
                f"🛠️ กำลังสร้างภาพ Debug Optical Flow สำหรับสถานี {station}...", 
                parse_mode="HTML"
            )
            
            from app.services.tmd_radar_processor import TMDRadarProcessor
            try:
                processor = TMDRadarProcessor(station)
                frames_data, _, _ = await processor.fetch_loop_gif_and_extract_frames()
                if not frames_data or len(frames_data) < 2:
                    await telegram.send_telegram_message(chat_id, "❌ ดึงภาพจาก TMD ไม่สำเร็จ หรือมีน้อยกว่า 2 เฟรม")
                    return
                    
                import cv2
                import numpy as np
                import asyncio
                
                prev_frame = cv2.resize(frames_data[-2], (800, 800), interpolation=cv2.INTER_NEAREST)
                curr_frame = cv2.resize(frames_data[-1], (800, 800), interpolation=cv2.INTER_NEAREST)
                
                # Resize all frames to 800x800 for the debug image generator
                resized_frames = [cv2.resize(f, (800, 800), interpolation=cv2.INTER_NEAREST) for f in frames_data]
                
                from app.services.weather_manager import _DEV_CONFIG
                
                images = await asyncio.to_thread(
                    processor.generate_multiframe_flow_debug_images,
                    resized_frames, 400, 400, _DEV_CONFIG.get("min_dbz", 10.0), _DEV_CONFIG.get("flow_mode", "latest")
                )
                
                await telegram.send_telegram_photo(chat_id, images["rain_mask"], "debug_1_rain_mask.png")
                await telegram.send_telegram_photo(chat_id, images["flow_hsv"], "debug_2_flow_hsv.png")
                await telegram.send_telegram_photo(chat_id, images["flow_grid"], "debug_3_flow_grid.png")
                await telegram.send_telegram_photo(chat_id, images["clusters"], "debug_4_clusters.png")
                
                await telegram.send_telegram_message(chat_id, "✅ ส่งภาพ Debug ครบแล้วครับ")
            except Exception as e:
                import traceback
                logger.error(f"visualize_flow error: {e}\n{traceback.format_exc()}")
                await telegram.send_telegram_message(chat_id, f"❌ Error: {e}")
            return
