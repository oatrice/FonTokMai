from fastapi import APIRouter, Request, BackgroundTasks
import httpx
import os
import logging
from datetime import datetime, timezone
from app.services.weather_manager import WeatherManager
from app.dependencies import get_repo_context
from app.services.telegram import (
    send_telegram_message,
    send_telegram_message_return_id,
    edit_telegram_message,
    answer_callback_query,
    get_radar_inline_keyboard,
    send_telegram_document,
    DEVELOPER_CHAT_IDS,
)
import json

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/telegram",
    tags=["webhook"]
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "mock_token")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
TELEGRAM_EDIT_REPLY_MARKUP_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageReplyMarkup"


def format_duration_text(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} นาที"
    hrs = minutes // 60
    mins = minutes % 60
    if mins > 0:
        return f"{hrs} ชม. {mins} นาที"
    return f"{hrs} ชม."


def _build_forecast_text(result: dict) -> str:
    """
    สร้างข้อความพยากรณ์ฝนจาก result dict ที่ได้จาก WeatherManager
    ใช้ร่วมกันทั้ง process_telegram_location และ handle_callback_query (raw data)
    """
    predictions = result.get("predictions", [])
    actual_endpoint = result.get("endpoint", "unknown")

    # แปลงชื่อ endpoint เป็นภาษามนุษย์
    endpoint_label_map = {
        "tomorrow": "Tomorrow.io",
        "rainbow-local": "Rainbow Local Radar",
        "rainbow-global": "Rainbow Global",
        "tmd-radar": "TMD Radar",
        "error": "ไม่สามารถเชื่อมต่อได้",
    }
    endpoint_label = endpoint_label_map.get(actual_endpoint, actual_endpoint)
    if actual_endpoint.startswith("tmd-radar (") and actual_endpoint.endswith(")"):
        endpoint_label = actual_endpoint.replace("tmd-radar", "TMD Radar", 1)

    # คำนวณ ETA
    eta_minutes = None
    if predictions:
        try:
            base_time = datetime.fromisoformat(predictions[0].get("time", "").replace("Z", "+00:00"))
        except Exception:
            base_time = None

        for pred in predictions:
            if pred.get("rain", 0) > 0:
                if base_time:
                    try:
                        pred_time = datetime.fromisoformat(pred.get("time", "").replace("Z", "+00:00"))
                        eta_minutes = int((pred_time - base_time).total_seconds() / 60)
                    except Exception:
                        eta_minutes = 0
                else:
                    eta_minutes = 0
                break

    if eta_minutes is not None or result.get("max_rain", 0) > 0:
        intensity_str = result.get("intensity", "ไม่ทราบ")
        duration_min = result.get("duration_minutes", 0)
        rain_summary = result.get("rain_summary")

        if rain_summary:
            text = f"🌧️ ข้อมูลพยากรณ์ฝน (ตรวจสอบด้วย: {endpoint_label})\n"
            text += f"{rain_summary}\n"
        else:
            if eta_minutes == 0 or (eta_minutes is None and result.get("max_rain", 0) > 0):
                text = f"🌧️ ฝนกำลังตกอยู่ที่พิกัดของคุณ ณ ขณะนี้ (ตรวจสอบด้วย: {endpoint_label})\n"
            else:
                text = f"🌧️ ฝนกำลังเคลื่อนมาทางทิศของคุณ จะเริ่มตกในอีก {format_duration_text(eta_minutes)} (ตรวจสอบด้วย: {endpoint_label})\n"
            
            if intensity_str == "ไม่มีฝน" and eta_minutes and eta_minutes > 0:
                text += f"💧 ความรุนแรง (คาดการณ์): ฝนกำลังจะมา\n"
            else:
                text += f"💧 ความรุนแรง: {intensity_str}\n"

            if duration_min > 0:
                text += f"⏱️ คาดว่าจะตกต่อเนื่องประมาณ: {format_duration_text(duration_min)}\n"
        
        wind_kmh = result.get("wind_speed_kmh", 0)
        wind_dir = result.get("wind_dir_text", "ไม่ทราบ")
        if wind_kmh > 0:
            if "tmd-radar" in actual_endpoint:
                if "ไม่พบฝน" not in result.get("rain_summary", ""):
                    text += f"🌬️ ทิศที่พายุเคลื่อนที่ไป: {wind_kmh} km/h (ทิศ {wind_dir})\n"
            else:
                text += f"🌬️ สภาพลม: {wind_kmh} km/h (ทิศ {wind_dir})\n"

        if not rain_summary:
            growth_rate = result.get("growth_rate_pct")
            if growth_rate is not None:
                if growth_rate > 5.0:
                    text += f"📈 แนวโน้มกลุ่มฝน: กำลังก่อตัวแรงขึ้น (+{growth_rate:.1f}%)\n"
                elif growth_rate < -5.0:
                    text += f"📉 แนวโน้มกลุ่มฝน: อ่อนกำลังลง ({growth_rate:.1f}%)\n"
                else:
                    text += f"➖ แนวโน้มกลุ่มฝน: คงที่\n"
    else:
        text = f"ยังไม่มีแนวโน้มฝนตกในบริเวณของคุณภายใน 1-2 ชั่วโมงนี้ (ตรวจสอบด้วย: {endpoint_label})\n"
        if "tmd-radar" in actual_endpoint:
            text += "\n(ระบบงดแสดงภาพ Timeline และ Zoom-in Tracking เนื่องจากตรวจไม่พบกลุ่มฝน)\n"

    return text, actual_endpoint, eta_minutes


async def process_telegram_location(
    chat_id: int,
    lat: float,
    lng: float,
    force_endpoint: str = None,
    message_id_to_edit: int = None,
    show_advanced: bool = False,
):
    """
    ดึงข้อมูลพยากรณ์ฝนผ่าน WeatherManager (รองรับ fallback chain อัตโนมัติ)
    และส่ง/แก้ไขข้อความผลลัพธ์กลับไปยัง Telegram

    พารามิเตอร์:
      force_endpoint: ถ้าระบุ ("global"/"local") จะบังคับใช้ endpoint นั้นโดยตรง
      message_id_to_edit: ถ้ามี ให้แก้ไขข้อความเดิม (loading state) แทนการส่งใหม่
    """
    try:
        async with get_repo_context() as repo:
            mock_state = await repo.get_mock_state(chat_id)

        weather_manager = WeatherManager()
        result = await weather_manager.predict_rain(
            lat, lng,
            mock_state=mock_state,
            force_endpoint=force_endpoint,
        )

        text, actual_endpoint, eta_minutes = _build_forecast_text(result)

        if result.get("is_outdated"):
            text = "⚠️ **ยังไม่มีข้อมูลล่าสุดจากกรมอุตุฯ (TMD Radar)**\nแนะนำให้เปลี่ยนไปใช้ API อื่น (เช่น Tomorrow.io หรือ Open-Meteo) แทนชั่วคราวครับ\n"

        # ถ้าทุก API พัง แสดงข้อความ error ชัดเจน แทนการบอกว่า "ไม่มีฝน"
        if actual_endpoint == "error":
            error_text = (
                "⚠️ ขออภัย ไม่สามารถเชื่อมต่อกับระบบพยากรณ์ฝนได้ในขณะนี้\n"
                "กรุณาลองใหม่อีกครั้งในภายหลัง"
            )
            if message_id_to_edit:
                await edit_telegram_message(chat_id, message_id_to_edit, error_text)
            else:
                await send_telegram_message(chat_id, error_text)
            return

        # ตรวจสอบ location ที่บันทึกไว้
        has_existing_loc = False
        async with get_repo_context() as repo:
            existing_loc = await repo.get_location(chat_id)
            if existing_loc:
                has_existing_loc = True

        # Round สำหรับ callback_data
        r_lat = round(lat, 4)
        r_lng = round(lng, 4)

        keyboard = []

        if has_existing_loc:
            text += "\n(คุณมีพิกัดเดิมบันทึกไว้อยู่แล้ว ต้องการบันทึกพิกัดนี้เป็นอะไร หรือลบของเดิมทิ้ง?)"
            keyboard.append([
                {"text": "🏠 บ้าน (2 ด.)", "callback_data": f"loc_save_Home_2m_{r_lat}_{r_lng}"},
                {"text": "🏠 บ้าน (ตป.)", "callback_data": f"loc_save_Home_inf_{r_lat}_{r_lng}"}
            ])
            keyboard.append([
                {"text": "💼 ที่ทำงาน (2 ด.)", "callback_data": f"loc_save_Work_2m_{r_lat}_{r_lng}"},
                {"text": "💼 ที่ทำงาน (ตป.)", "callback_data": f"loc_save_Work_inf_{r_lat}_{r_lng}"}
            ])
            keyboard.append([
                {"text": "📍 ทั่วไป (2 ด.)", "callback_data": f"loc_save_Default_2m_{r_lat}_{r_lng}"},
                {"text": "📍 ทั่วไป (ตป.)", "callback_data": f"loc_save_Default_inf_{r_lat}_{r_lng}"}
            ])
        else:
            text += "(คุณต้องการให้ระบบจดจำตำแหน่งนี้สำหรับการแจ้งเตือนอัตโนมัติไหม?)"
            keyboard.append([
                {"text": "🏠 บ้าน (2 ด.)", "callback_data": f"loc_save_Home_2m_{r_lat}_{r_lng}"},
                {"text": "🏠 บ้าน (ตป.)", "callback_data": f"loc_save_Home_inf_{r_lat}_{r_lng}"}
            ])
            keyboard.append([
                {"text": "💼 ที่ทำงาน (2 ด.)", "callback_data": f"loc_save_Work_2m_{r_lat}_{r_lng}"},
                {"text": "💼 ที่ทำงาน (ตป.)", "callback_data": f"loc_save_Work_inf_{r_lat}_{r_lng}"}
            ])
            keyboard.append([
                {"text": "📍 ทั่วไป (2 ด.)", "callback_data": f"loc_save_Default_2m_{r_lat}_{r_lng}"},
                {"text": "📍 ทั่วไป (ตป.)", "callback_data": f"loc_save_Default_inf_{r_lat}_{r_lng}"}
            ])
            keyboard.append([{"text": "❌ ไม่เป็นไร", "callback_data": "loc_no"}])

        # ปุ่มเปรียบเทียบข้อมูล (Issue #53)
        keyboard.append([{"text": "📊 เปรียบเทียบข้อมูล 4 API", "callback_data": f"compare_api_{r_lat}_{r_lng}"}])

        # ปุ่มสลับ Endpoint
        if actual_endpoint in ("rainbow-local", "local", "tmd-radar", "tmd-radar (kkn120)", "tmd-radar (kkn240)", "tmd-radar (skn240)"):
            keyboard.append([{"text": "🔄 สลับไปใช้ Global", "callback_data": f"switch_global_{r_lat}_{r_lng}"}])
        else:
            keyboard.append([{"text": "🔄 สลับไปใช้ Local Radar", "callback_data": f"switch_radar_{r_lat}_{r_lng}"}])

        reply_markup = {"inline_keyboard": keyboard}

        logger.info(f"Preparing to send message to chat_id={chat_id}: '{text[:80]}...'")

        if message_id_to_edit:
            await edit_telegram_message(chat_id, message_id_to_edit, text, reply_markup)
        else:
            await send_telegram_message(chat_id, text, reply_markup)
            
        gif_bytes = result.get("radar_gif_bytes")
        hq_gif_bytes = result.get("radar_hq_gif_bytes")
        static_bytes = result.get("radar_static_bytes")
        tracking_bytes = result.get("radar_tracking_bytes")
        timeline_bytes = result.get("rain_timeline_bytes")
        
        from app.services.telegram import send_telegram_photo, send_telegram_document, send_telegram_raw_document
        
        if static_bytes:
            await send_telegram_photo(chat_id, static_bytes, "radar_latest.png")
            
        if timeline_bytes:
            await send_telegram_photo(chat_id, timeline_bytes, "rain_timeline.png")
            
        if tracking_bytes:
            await send_telegram_photo(chat_id, tracking_bytes, "radar_tracking.png")
            
        if gif_bytes:
            await send_telegram_document(chat_id, gif_bytes, "radar_nowcast.gif")
        if hq_gif_bytes:
            await send_telegram_raw_document(chat_id, hq_gif_bytes, "radar_nowcast_full.gif")

        if show_advanced:
            advanced_data = await weather_manager.get_advanced_alerts(lat, lng, mock_state=mock_state)
            has_advisory = len(advanced_data.get("advisories", [])) > 0
            has_lightning = advanced_data.get("lightning") is not None
            has_stormcell = advanced_data.get("stormcell") is not None
            
            if has_advisory or has_lightning or has_stormcell:
                adv_text = "🚨 *ข้อมูลเตือนภัยขั้นสูงรอบตัวคุณ*\n\n"
                
                if has_advisory:
                    for adv in advanced_data["advisories"]:
                        adv_text += f"⚠️ ประกาศเตือนภัย: {adv.get('name', '')}\n"
                    adv_text += "\n"
                    
                if has_lightning:
                    lightning = advanced_data["lightning"]
                    adv_text += f"⚡ ฟ้าผ่าระยะใกล้สุด: {lightning.get('distance_km', 0):.1f} กม.\n\n"
                    
                if has_stormcell:
                    stormcell = advanced_data["stormcell"]
                    if stormcell.get('distance_km') is None:
                        adv_text += f"🌪️ แนวโน้มกลุ่มฝน/ลม (Contingency):\n"
                        adv_text += f"   - ทิศทาง: {stormcell.get('direction', 'N/A')}\n"
                        adv_text += f"   - ความเร็วลม: {stormcell.get('speed_kmh', 0):.1f} km/h\n\n"
                        adv_text += "ℹ️ ข้อมูลขั้นสูงจาก Open-Meteo (Fallback)"
                    else:
                        adv_text += f"🌪️ ตรวจพบกลุ่มพายุ: ระยะห่าง {stormcell.get('distance_km', 0):.1f} กม.\n"
                        adv_text += f"   - ทิศทาง: {stormcell.get('direction', 'N/A')}\n"
                        adv_text += f"   - ความเร็ว: {stormcell.get('speed_kmh', 0):.1f} km/h\n"
                        adv_text += f"   - ความรุนแรงสูงสุด (dBZ): {stormcell.get('max_dbz', 0)}\n\n"
                        adv_text += "ℹ️ ข้อมูลขั้นสูงจาก Xweather"
                elif has_advisory or has_lightning:
                    adv_text += "ℹ️ ข้อมูลขั้นสูงจาก Xweather"
                
                await send_telegram_message(chat_id, adv_text)
            else:
                await send_telegram_message(chat_id, "ℹ️ ข้อมูลเตือนภัยขั้นสูง: ไม่พบประกาศเตือนภัย พายุ หรือฟ้าผ่าในระยะใกล้")

    except Exception as e:
        logger.error(f"Error processing telegram location: {e}")
        error_text = "ขออภัย ไม่สามารถดึงข้อมูลพยากรณ์ฝนได้ในขณะนี้"
        try:
            if message_id_to_edit:
                await edit_telegram_message(chat_id, message_id_to_edit, error_text)
            else:
                await send_telegram_message(chat_id, error_text)
        except Exception as inner_e:
            logger.error(f"Failed to send fallback error message: {inner_e}")


async def handle_callback_query(callback_query: dict):
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
            # Example: loc_save_Home_2m_13.1_100.1
            if len(parts) >= 6:
                try:
                    name = parts[2].lower()  # e.g. "home", "work", "default"
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
        if str(chat_id) not in DEVELOPER_CHAT_IDS:
            answer_text = "คุณไม่มีสิทธิ์เข้าถึงข้อมูลดิบ"
        else:
            parts = data.split("_")
            if len(parts) >= 3:
                try:
                    lat = float(parts[1])
                    lng = float(parts[2])

                    # ดึงข้อมูลผ่าน WeatherManager (รองรับ fallback chain)
                    weather_manager = WeatherManager()
                    result = await weather_manager.predict_rain(lat, lng)

                    logger.info(f"Raw API Data for {lat}, {lng}: {json.dumps(result)}")

                    raw_bytes = json.dumps(result, indent=2).encode("utf-8")
                    await send_telegram_document(chat_id, raw_bytes, f"raw_{lat}_{lng}.json")
                    answer_text = "ส่งไฟล์ข้อมูลดิบเรียบร้อยแล้ว"
                except Exception as e:
                    logger.error(f"Error fetching raw data: {e}")
                    answer_text = "เกิดข้อผิดพลาดในการดึงข้อมูลดิบ"
            else:
                answer_text = "รูปแบบข้อมูลดิบไม่ถูกต้อง"

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
                
                loading_msg_id = await send_telegram_message_return_id(chat_id, f"⏳ กำลังประมวลผลสภาพอากาศด้วย {provider}...")
                await process_telegram_location(chat_id, lat, lng, force_endpoint=provider, message_id_to_edit=loading_msg_id)
                await answer_callback_query(query_id)
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
                
                weather_manager = WeatherManager()
                results = await weather_manager.compare_all_apis(lat, lng, mock_state=mock_state)
                
                # Format results
                from datetime import datetime, timezone, timedelta
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
                            # Replace newlines with indent
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
                                # Calculate ETA
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
                
                await edit_telegram_message(chat_id, message_id, text, reply_markup=reply_markup)
                
                await answer_callback_query(query_id)
                
            except Exception as e:
                logger.error(f"Error handling compare_api: {e}")
                answer_text = "เกิดข้อผิดพลาดในการดึงข้อมูลเปรียบเทียบ"

    await answer_callback_query(query_id, text=answer_text)
    
    async with httpx.AsyncClient() as client:
        # ลบ Inline Keyboard (เฉพาะ action ที่เกี่ยวกับ location ไม่ใช่ raw/switch)
        if message_id and not (data.startswith("raw_") or data.startswith("switch_")):
            await client.post(TELEGRAM_EDIT_REPLY_MARKUP_URL, json={
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_markup": {"inline_keyboard": []}
            })


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

    await send_telegram_message(chat_id, text, reply_markup)


async def handle_radar_command(chat_id: int):
    async with get_repo_context() as repo:
        loc = await repo.get_location(chat_id)

    if not loc:
        text = "คุณยังไม่ได้บันทึกตำแหน่งใดๆ ไว้ในระบบ กรุณาส่งพิกัด Location ของคุณให้บอทก่อนครับ 📍"
        await send_telegram_message(chat_id, text)
    else:
        text = "📡 คุณสามารถเช็คเรดาร์ฝนด้วยตัวเองได้จากแหล่งข้อมูลเหล่านี้:"
        is_dev = str(chat_id) in DEVELOPER_CHAT_IDS
        reply_markup = get_radar_inline_keyboard(loc.latitude, loc.longitude, is_developer=is_dev)
        await send_telegram_message(chat_id, text, reply_markup=reply_markup)


async def handle_tmd_fallback_command(chat_id: int, command: str):
    """
    /tmd_fallback on
    /tmd_fallback off
    """
    if str(chat_id) not in DEVELOPER_CHAT_IDS:
        return

    parts = command.strip().split()
    if len(parts) < 2:
        async with get_repo_context() as repo:
            sys_settings = await repo.get_system_settings()
            current_status = sys_settings.get("enable_gif_fallback", True)
            
        status_str = "ON 🟢" if current_status else "OFF 🔴"
        await send_telegram_message(
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
    await send_telegram_message(
        chat_id,
        f"✅ ตั้งค่า GIF Fallback เป็น {status_str} เรียบร้อยแล้ว"
    )


async def handle_devmock_command(chat_id: int, command: str):
    if str(chat_id) not in DEVELOPER_CHAT_IDS:
        return

    async with get_repo_context() as repo:
        if command == "/devmock rain":
            await repo.set_mock_state(chat_id, "rain")

            # Reset cooldown สำหรับทุก location ของ user นี้ เพื่อให้ alert ยิงทันที
            locs = await repo.get_user_locations(chat_id)
            for loc in locs:
                await repo.update_last_alerted(loc, None)

            await send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: 🌧️ ฝนตกหนัก (Boost เมฆจริง)\n⏳ กำลังสร้างแจ้งเตือน...")

            from app.scheduler_tasks import check_rain_and_alert
            await check_rain_and_alert()
            
        elif command == "/devmock storm":
            await repo.set_mock_state(chat_id, "storm")

            # Reset cooldown สำหรับทุก location ของ user นี้ เพื่อให้ alert ยิงทันที
            locs = await repo.get_user_locations(chat_id)
            for loc in locs:
                await repo.update_last_alerted(loc, None)

            await send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: 🌪️ พายุจำลอง (สร้างเมฆปลอม 5 สี)\n⏳ กำลังสร้างแจ้งเตือน...")

            from app.scheduler_tasks import check_rain_and_alert
            await check_rain_and_alert()
            
        elif command == "/devmock clear":
            await repo.set_mock_state(chat_id, "clear")
            await send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: ☀️ ท้องฟ้าแจ่มใส\n⏳ กำลังตรวจสอบสภาพอากาศ...")
            
            from app.scheduler_tasks import check_rain_and_alert
            await check_rain_and_alert()
            
        elif command == "/devmock error":
            await repo.set_mock_state(chat_id, "error")
            await send_telegram_message(chat_id, "🛠️ [DEV MOCK] เปิดใช้งานโหมดจำลองสถานการณ์: ❌ เชื่อมต่อ API ล้มเหลวทั้งหมด\n⏳ กำลังส่งตำแหน่งเพื่อทดสอบ Fallback...")
            
            # Simulate a location update to trigger the fallback error message immediately
            locs = await repo.get_user_locations(chat_id)
            if locs:
                await process_telegram_location(chat_id, locs[0].latitude, locs[0].longitude, message_id_to_edit=None)
            else:
                await send_telegram_message(chat_id, "ไม่พบตำแหน่งที่บันทึกไว้ โปรดส่ง Location มาใหม่เพื่อทดสอบ error")
            
        elif command == "/devmock off":
            await repo.set_mock_state(chat_id, None)
            await send_telegram_message(chat_id, "🛠️ [DEV MOCK] ปิดใช้งานโหมดจำลองเรียบร้อยแล้ว\n⏳ กำลังส่งสถานะ All-Clear...")
            
            from app.scheduler_tasks import check_rain_and_alert
            await check_rain_and_alert()


async def handle_rain_command(chat_id: int, command: str, show_advanced: bool = False):
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
            await send_telegram_message(chat_id, "⚠️ ไม่พบพิกัดที่บันทึกไว้ กรุณาส่ง Location ให้บอทก่อนครับ")
            return
            
        if target_location_name:
            for l in locs:
                if (l.name and l.name.lower() == target_location_name) or (target_location_name == "default" and l.name is None):
                    loc = l
                    break
            if not loc:
                available_locs = ", ".join([l.name for l in locs if l.name])
                await send_telegram_message(chat_id, f"⚠️ ไม่พบพิกัดชื่อ '{target_location_name}'\nพิกัดที่มี: {available_locs or 'default'}")
                return
        else:
            loc = locs[0]
        
    loc_display = loc.name.capitalize() if loc.name else "ระบบอัตโนมัติ"
    msg_text = f"⏳ กำลังตรวจสอบสภาพอากาศที่ '{loc_display}' "
    if force_provider:
        msg_text += f"จาก {force_provider}..."
    else:
        msg_text += "..."
        
    loading_msg_id = await send_telegram_message_return_id(chat_id, msg_text)
    
    await process_telegram_location(
        chat_id, lat=loc.latitude, lng=loc.longitude,
        force_endpoint=force_provider, message_id_to_edit=loading_msg_id,
        show_advanced=show_advanced
    )


@router.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()

    if "callback_query" in payload:
        await handle_callback_query(payload["callback_query"])
        return {"status": "ok"}

    if "message" in payload:
        message = payload["message"]
        chat_id = message.get("chat", {}).get("id")
        date_ts = message.get("date", 0)

        # Handle pending updates: ignore messages older than 2 minutes (120 seconds)
        current_ts = datetime.now(timezone.utc).timestamp()
        if date_ts > 0 and (current_ts - date_ts) > 120:
            logger.warning(f"[WEBHOOK] Ignoring stale message from chat_id={chat_id} (age: {current_ts - date_ts:.1f}s)")
            return {"status": "ok", "ignored": "stale"}

        if "location" in message and chat_id:
            location = message["location"]
            lat = location.get("latitude")
            lng = location.get("longitude")

            if lat and lng:
                # ส่งข้อความตอบกลับทันทีเพื่อให้ผู้ใช้รู้ว่าบอทได้รับข้อมูลแล้ว
                loading_msg_id = await send_telegram_message_return_id(
                    chat_id,
                    "⏳ กำลังประมวลผลเรดาร์และพยากรณ์อากาศ กรุณารอสักครู่..."
                )
                from app.services.cloud_tasks import CloudTasksService
                tasks_svc = CloudTasksService()
                payload = {
                    "chat_id": chat_id, "lat": lat, "lng": lng,
                    "message_id_to_edit": loading_msg_id
                }
                if not tasks_svc.enqueue_task("worker/process-telegram-location", payload):
                    # ส่ง message_id ไปให้ background task เพื่อ edit ต่อเมื่อเสร็จ
                    background_tasks.add_task(
                        process_telegram_location, chat_id, lat, lng,
                        None, loading_msg_id
                    )
                return {"status": "ok"}

        text = message.get("text", "")
        logger.info(f"[WEBHOOK] Received text='{text}' chat_id={chat_id}")

        from app.services.cloud_tasks import CloudTasksService
        tasks_svc = CloudTasksService()

        if text.startswith("/mylocation") and chat_id:
            if not tasks_svc.enqueue_task("worker/handle-mylocation", {"chat_id": chat_id}):
                background_tasks.add_task(handle_mylocation_command, chat_id)
            return {"status": "ok"}

        if text.startswith("/radar") and chat_id:
            if not tasks_svc.enqueue_task("worker/handle-radar", {"chat_id": chat_id}):
                background_tasks.add_task(handle_radar_command, chat_id)
            return {"status": "ok"}

        if text.startswith("/rain_pro") and chat_id:
            if not tasks_svc.enqueue_task("worker/handle-rain", {"chat_id": chat_id, "command": text, "show_advanced": True}):
                background_tasks.add_task(handle_rain_command, chat_id, text, show_advanced=True)
            return {"status": "ok"}

        if text.startswith("/rain") and chat_id:
            if not tasks_svc.enqueue_task("worker/handle-rain", {"chat_id": chat_id, "command": text}):
                background_tasks.add_task(handle_rain_command, chat_id, text)
            return {"status": "ok"}

        if text.startswith("/devmock") and chat_id:
            if not tasks_svc.enqueue_task("worker/handle-devmock", {"chat_id": chat_id, "command": text.strip()}):
                background_tasks.add_task(handle_devmock_command, chat_id, text.strip())
            return {"status": "ok"}

        if text.startswith("/tmd_fallback") and chat_id:
            background_tasks.add_task(handle_tmd_fallback_command, chat_id, text.strip())
            return {"status": "ok"}

        # /check — shorthand alias for /rain tmd-radar (for manual testing)
        if text.strip() == "/check" and chat_id:
            logger.info(f"[WEBHOOK] /check received from chat_id={chat_id}, routing to handle_rain_command with 'tmd-radar'")
            if not tasks_svc.enqueue_task("worker/handle-rain", {"chat_id": chat_id, "command": "/rain tmd-radar"}):
                background_tasks.add_task(handle_rain_command, chat_id, "/rain tmd-radar")
            return {"status": "ok"}

        logger.debug(f"[WEBHOOK] Unrecognized command or text, returning ignored. text='{text}'")

    return {"status": "ignored"}
