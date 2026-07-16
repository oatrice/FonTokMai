import os
import json
import httpx
import logging
from datetime import datetime, timezone, timedelta
from app.services import weather_manager
from app.dependencies import get_repo_context
from app.routers.webhook_location import process_telegram_location
from app.routers.webhook_utils import check_admin_access, format_duration_text
from app.services import telegram

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "mock_token")
TELEGRAM_EDIT_REPLY_MARKUP_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageReplyMarkup"

async def handle_callback_query(callback_query: dict, already_answered: bool = False):
    query_id = callback_query.get("id")
    from_user = callback_query.get("from", {})
    chat_id = from_user.get("id")
    data = callback_query.get("data", "")
    message = callback_query.get("message", {})
    message_id = message.get("message_id")

    if not chat_id or not query_id:
        return

    answer_text = ""
    async with get_repo_context() as repo:
        if data.startswith("loc_save_"):
            parts = data.split("_")
            # Format: loc_save_<name>_<retention>_<lat>_<lng>
            if len(parts) >= 6:
                try:
                    name = parts[2].lower()
                    retention_str = parts[3]
                    lat = float(parts[4])
                    lng = float(parts[5])
                    retention = "TWO_MONTHS" if retention_str == "2m" else "FOREVER"
                    await repo.save_location(chat_id, lat, lng, retention, name)
                    answer_text = f"บันทึกข้อมูลพิกัด {name} เรียบร้อยแล้ว"
                except ValueError:
                    answer_text = "เกิดข้อผิดพลาดในการบันทึกพิกัด"
        elif data.startswith("loc_del_"):
            parts = data.split("_")
            if len(parts) >= 3:
                name = parts[2].lower()
                await repo.delete_location(chat_id, name)
                answer_text = f"ลบข้อมูลพิกัด {name} เรียบร้อยแล้ว"
        elif data == "loc_no":
            answer_text = "ระบบรับทราบ จะไม่จดจำตำแหน่งใหม่"
        elif data.startswith("fb_falsealarm_"):
            parts = data.split("_")
            if len(parts) >= 4:
                try:
                    lat = float(parts[2])
                    lng = float(parts[3])
                    
                    context_msg = "User reported false alarm from inline button"
                    if len(parts) >= 6:
                        ep_map_rev = {"t": "Tomorrow.io", "rl": "Rainbow Local", "rg": "Rainbow Global", "xw": "Xweather", "om": "Open-Meteo", "u": "Unknown"}
                        ep_name = ep_map_rev.get(parts[4], parts[4])
                        max_r = parts[5]
                        context_msg = f"Source: {ep_name}, max_rain: {max_r} mm/hr"
                        
                    await repo.save_feedback(chat_id, lat, lng, "false_alarm", context_msg)
                    answer_text = "ขอบคุณสำหรับข้อมูล เราจะนำไปปรับปรุงความแม่นยำครับ"
                except Exception as e:
                    logger.error(f"Error parsing false alarm data: {e}")
                    answer_text = "เกิดข้อผิดพลาดในการบันทึกข้อมูล"

    # Handle Developer Raw Data Request
    if data.startswith("raw_"):
        if not await check_admin_access(chat_id):
            answer_text = "คุณไม่มีสิทธิ์เข้าถึงข้อมูลดิบ"
        else:
            parts = data.split("_")
            if len(parts) >= 3:
                try:
                    lat = float(parts[1])
                    lng = float(parts[2])

                    wm = weather_manager.WeatherManager()
                    result = await wm.predict_rain(lat, lng, chat_id=chat_id)

                    logger.info(f"Raw API Data for {lat}, {lng}: {json.dumps(result)}")

                    raw_bytes = json.dumps(result, indent=2).encode("utf-8")
                    await telegram.send_telegram_document(chat_id, raw_bytes, f"raw_{lat}_{lng}.json")
                    answer_text = "ส่งไฟล์ข้อมูลดิบเรียบร้อยแล้ว"
                except Exception as e:
                    logger.error(f"Error fetching raw data: {e}")
                    answer_text = "เกิดข้อผิดพลาดในการดึงข้อมูลดิบ"
            else:
                answer_text = "รูปแบบข้อมูลดิบไม่ถูกต้อง"

    # Handle Manual target lock callbacks
    if data.startswith("lock_target_"):
        parts = data.split("_")
        if len(parts) >= 5:
            try:
                lat = float(parts[2])
                lng = float(parts[3])
                label = parts[4]
                
                answer_text = f"กำลังล็อคเป้ากลุ่มฝน [{label}]..."
                
                wm = weather_manager.WeatherManager()
                res = await wm.predict_rain(lat, lng, chat_id=chat_id)
                clouds = res.get("approaching_clouds", [])
                all_clusters = res.get("all_rain_clusters", [])
                
                target_c = None
                for c in clouds:
                    if c.get("label") == label:
                        target_c = c
                        break
                if not target_c:
                    for c in all_clusters:
                        if c.get("label") == label:
                            target_c = c
                            break
                
                if target_c:
                    cx = target_c["cx"]
                    cy = target_c["cy"]
                    async with get_repo_context() as repo:
                        all_locs = await repo.get_user_locations(chat_id)
                        chosen_name = "default"
                        for l in all_locs:
                            if (abs(l.latitude - lat) < 1e-6
                                    and abs(l.longitude - lng) < 1e-6):
                                chosen_name = l.name
                                break
                        else:
                            await repo.save_location(
                                chat_id, lat, lng, "FOREVER", name="default"
                            )
                        await repo.update_tracking_mode(
                            chat_id=chat_id,
                            tracking_mode="manual",
                            locked_target_id=label,
                            locked_target_cx=cx,
                            locked_target_cy=cy,
                            name=chosen_name,
                        )
                    await process_telegram_location(
                        chat_id, lat, lng,
                        message_id_to_edit=message_id,
                        location_name=chosen_name,
                    )
                else:
                    answer_text = f"ไม่พบกลุ่มฝน [{label}] หรือเมฆสลายตัวไปแล้ว"
            except Exception as e:
                logger.error(f"Error handling lock target callback: {e}")
                answer_text = "เกิดข้อผิดพลาดในการล็อคเป้า"

    elif data.startswith("unlock_target_"):
        parts = data.split("_")
        if len(parts) >= 4:
            try:
                lat = float(parts[2])
                lng = float(parts[3])
                
                answer_text = "กำลังปลดล็อคกลุ่มฝน..."
                
                async with get_repo_context() as repo:
                    await repo.update_tracking_mode(
                        chat_id=chat_id,
                        tracking_mode="auto",
                    )
                await process_telegram_location(
                    chat_id, lat, lng,
                    message_id_to_edit=message_id,
                )
            except Exception as e:
                logger.error(f"Error handling unlock target callback: {e}")
                answer_text = "เกิดข้อผิดพลาดในการปลดล็อคเป้า"

    # Handle Endpoint Switch (พร้อม Loading State)
    if data.startswith("switch_radar_") or data.startswith("switch_global_"):
        parts = data.split("_")
        if len(parts) >= 4:
            try:
                lat = float(parts[2])
                lng = float(parts[3])
                force_endpoint = "local" if data.startswith("switch_radar_") else "global"

                answer_text = "กำลังดึงข้อมูลใหม่..."
                await process_telegram_location(
                    chat_id, lat, lng,
                    force_endpoint=force_endpoint,
                    message_id_to_edit=message_id,
                )
            except Exception as e:
                logger.error(f"Error handling switch endpoint: {e}")
                answer_text = "เกิดข้อผิดพลาดในการสลับแหล่งข้อมูล"

    # Handle Force API
    elif data.startswith("force_api_"):
        parts = data.split("_")
        if len(parts) >= 5:
            provider = parts[2]
            try:
                lat = float(parts[3])
                lng = float(parts[4])
                
                loading_msg_id = await telegram.send_telegram_message_return_id(chat_id, f"⏳ กำลังประมวลผลสภาพอากาศด้วย {provider}...")
                await process_telegram_location(chat_id, lat, lng, force_endpoint=provider, message_id_to_edit=loading_msg_id)
                if not already_answered:
                    await telegram.answer_callback_query(query_id)
            except ValueError:
                logger.error("Invalid lat/lng in force_api")

    # Handle View Insights (Issue #42)
    if data.startswith("compare_api_"):
        parts = data.split("_")
        if len(parts) >= 4:
            try:
                lat = float(parts[2])
                lng = float(parts[3])
                
                answer_text = "กำลังดึงข้อมูลเปรียบเทียบ..."
                
                async with get_repo_context() as repo:
                    mock_state = await repo.get_mock_state(chat_id)
                
                wm = weather_manager.WeatherManager()
                results = await wm.compare_all_apis(lat, lng, mock_state=mock_state)
                
                bkk_tz = timezone(timedelta(hours=7))
                update_time_str = datetime.now(bkk_tz).strftime("%d/%m/%Y %H:%M:%S")
                text = f"📊 ข้อมูลเปรียบเทียบ 4 API (พิกัด {lat}, {lng}):\n"
                text += f"🔄 ข้อมูลอัปเดตล่าสุด: {update_time_str}\n\n"
                
                display_names = {
                    "xweather": "Xweather (Premium)",
                    "tomorrow": "Tomorrow.io",
                    "rainbow-local": "Rainbow Local",
                    "rainbow-global": "Rainbow Global"
                }
                for k, v in results.items():
                    disp_k = display_names.get(k, k)
                    accuracy = v.get("accuracy_score", 0.0)
                    acc_percent = accuracy * 100.0
                    
                    if "error" in v:
                        text += f"🔹 {disp_k} (ความแม่นยำ: {acc_percent:.1f}%):\n  ❌ ข้อผิดพลาด: {v['error']}\n\n"
                    else:
                        max_rain = v.get('max_rain', 0)
                        text += f"🔹 {disp_k} (ความแม่นยำ: {acc_percent:.1f}%):\n"
                        
                        rain_summary = v.get("rain_summary")
                        if rain_summary:
                            indented_summary = rain_summary.replace("\n", "\n  ")
                            text += f"  {indented_summary}\n"
                            
                            wind_kmh = v.get("wind_speed_kmh", 0)
                            wind_dir = v.get("wind_dir_text", "ไม่ทราบ")
                            if wind_kmh > 0:
                                if "tmd-radar" in disp_k.lower() or "tmd-radar" in k.lower():
                                    if "ไม่พบฝน" not in rain_summary:
                                        text += f"  🌬️ ทิศที่พายุเคลื่อนที่ไป: {wind_kmh} km/h (ทิศ {wind_dir})\n"
                                else:
                                    text += f"  🌬️ ลม: {wind_kmh} km/h (ทิศ {wind_dir})\n"
                            text += "\n"
                        else:
                            text += f"  💧 ปริมาณฝนสูงสุด: {max_rain:.2f} mm/hr\n"
                            text += f"  🌧️ ความรุนแรง: {v.get('intensity', 'ไม่ทราบ')}\n"
                            
                            wind_kmh = v.get("wind_speed_kmh", 0)
                            wind_dir = v.get("wind_dir_text", "ไม่ทราบ")
                            if wind_kmh > 0:
                                if "tmd-radar" in disp_k.lower() or "tmd-radar" in k.lower():
                                    if "ไม่พบฝน" not in v.get("rain_summary", ""):
                                        text += f"  🌬️ ทิศที่พายุเคลื่อนที่ไป: {wind_kmh} km/h (ทิศ {wind_dir})\n"
                                else:
                                    text += f"  🌬️ ลม: {wind_kmh} km/h (ทิศ {wind_dir})\n"
                                
                            storm_distance = v.get("storm_distance_km")
                            if storm_distance is not None:
                                text += f"  🌪️ ระยะห่างพายุ: {storm_distance} กม.\n"
                            
                            if max_rain > 0:
                                eta_minutes = None
                                predictions = v.get("predictions", [])
                                if predictions:
                                    try:
                                        base_time = datetime.fromisoformat(predictions[0].get("time", "").replace("Z", "+00:00"))
                                        for pred in predictions:
                                            if pred.get("rain", 0) > 0:
                                                pred_time = datetime.fromisoformat(pred.get("time", "").replace("Z", "+00:00"))
                                                eta_minutes = int((pred_time - base_time).total_seconds() / 60)
                                                break
                                    except Exception:
                                        pass
                                        
                                duration = v.get("duration_minutes", 0)
                                
                                if eta_minutes is not None:
                                    start_dt = datetime.now(bkk_tz) + timedelta(minutes=eta_minutes)
                                    end_dt = start_dt + timedelta(minutes=duration)
                                    start_str = start_dt.strftime("%H:%M")
                                    end_str = end_dt.strftime("%H:%M")
                                    
                                    if eta_minutes == 0:
                                        text += f"  ⏱️ เริ่มตก: ขณะนี้ ({start_str} น.)\n"
                                    else:
                                        text += f"  ⏱️ เริ่มตกในอีก: {format_duration_text(eta_minutes)} ({start_str} น.)\n"
                                        
                                    if duration > 0:
                                        text += f"  ⏳ ตกต่อเนื่อง: {format_duration_text(duration)} (จนถึง {end_str} น.)\n"
                                    
                            text += "\n"
                
                keyboard = []
                row = []
                for ep in results.keys():
                    row.append({"text": f"✅ {display_names.get(ep, ep)}", "callback_data": f"force_api_{ep}_{lat}_{lng}"})
                    if len(row) == 2:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)
                reply_markup = {"inline_keyboard": keyboard}
                
                await telegram.edit_telegram_message(chat_id, message_id, text, reply_markup=reply_markup)
                
                if not already_answered:
                    await telegram.answer_callback_query(query_id)
                
            except Exception as e:
                logger.error(f"Error handling compare_api: {e}")
                answer_text = "เกิดข้อผิดพลาดในการดึงข้อมูลเปรียบเทียบ"

    if not already_answered:
        await telegram.answer_callback_query(query_id, text=answer_text)
    
    async with httpx.AsyncClient() as client:
        # ลบ Inline Keyboard
        if message_id and not (data.startswith("raw_") or data.startswith("switch_")):
            await client.post(TELEGRAM_EDIT_REPLY_MARKUP_URL, json={
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_markup": {"inline_keyboard": []}
            })
