import logging
from app.services import weather_manager
from app.dependencies import get_repo_context
from app.routers.webhook_utils import (
    LAST_ACTIVE_LOCATION,
    _reply,
    _build_forecast_text
)
from app.services import telegram

logger = logging.getLogger(__name__)

async def process_telegram_location(
    chat_id: int,
    lat: float,
    lng: float,
    force_endpoint: str = None,
    message_id_to_edit: int = None,
    show_advanced: bool = False,
    location_name: str = None,
    is_lock_command: bool = False,
):
    """
    ดึงข้อมูลพยากรณ์ฝนผ่าน WeatherManager (รองรับ fallback chain อัตโนมัติ)
    และส่ง/แก้ไขข้อความผลลัพธ์กลับไปยัง Telegram

    พารามิเตอร์:
      force_endpoint: ถ้าระบุ ("global"/"local") จะบังคับใช้ endpoint นั้นโดยตรง
      message_id_to_edit: ถ้ามี ให้แก้ไขข้อความเดิม (loading state) แทนการส่งใหม่
      location_name: ชื่อของสถานที่ที่จะแสดงในข้อความผลลัพธ์
    """
    try:
        if location_name:
            LAST_ACTIVE_LOCATION[chat_id] = location_name.lower()
        async with get_repo_context() as repo:
            mock_state = await repo.get_mock_state(chat_id)
            if not is_lock_command:
                locs = await repo.get_user_locations(chat_id)
                for loc in locs:
                    if loc.tracking_mode == "manual":
                        await repo.update_tracking_mode(
                            chat_id=chat_id,
                            tracking_mode="auto",
                            locked_target_id=None,
                            locked_target_cx=None,
                            locked_target_cy=None,
                            name=loc.name
                        )

        wm = weather_manager.WeatherManager()
        result = await wm.predict_rain(
            lat, lng,
            mock_state=mock_state,
            force_endpoint=force_endpoint,
            location_name=location_name,
            chat_id=chat_id,
        )

        text, actual_endpoint, eta_minutes = _build_forecast_text(result)
        
        if location_name:
            text = f"📍 **พื้นที่:** {location_name}\n\n" + text

        if result.get("is_outdated"):
            text = "⚠️ **ยังไม่มีข้อมูลล่าสุดจากกรมอุตุฯ (TMD Radar)**\nแนะนำให้เปลี่ยนไปใช้ API อื่น (เช่น Tomorrow.io หรือ Open-Meteo) แทนชั่วคราวครับ\n"

        # ถ้าทุก API พัง แสดงข้อความ error ชัดเจน แทนการบอกว่า "ไม่มีฝน"
        if actual_endpoint == "error":
            error_text = (
                "⚠️ ขออภัย ไม่สามารถเชื่อมต่อกับระบบพยากรณ์ฝนได้ในขณะนี้\n"
                "กรุณาลองใหม่อีกครั้งในภายหลัง"
            )
            await _reply(chat_id, error_text, message_id_to_edit)
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
        keyboard.append([{"text": "📊 เปรียบเทียบข้อมูลจากทุกแหล่ง", "callback_data": f"compare_api_{r_lat}_{r_lng}"}])

        # ปุ่มควบคุมเป้าเรดาร์แบบแมนนวล (Manual Cloud Targeting)
        if "tmd-radar" in actual_endpoint:
            t_mode = result.get("tracking_mode", "auto")
            if t_mode == "manual":
                locked_lbl = result.get("locked_target_id", "")
                keyboard.append([{"text": f"🔓 ปลดล็อค {locked_lbl} (Auto-track)", "callback_data": f"unlock_target_{r_lat}_{r_lng}"}])
            else:
                approaching_clouds = result.get("approaching_clouds", [])
                all_rain_clusters = result.get("all_rain_clusters", [])
                
                lock_buttons = []
                added_labels = set()
                
                for c in approaching_clouds:
                    lbl = c.get("label")
                    if lbl and lbl != "?" and lbl not in added_labels:
                        lock_buttons.append({"text": f"🔒 ล็อคเป้า {lbl}", "callback_data": f"lock_target_{r_lat}_{r_lng}_{lbl}"})
                        added_labels.add(lbl)
                        
                # Filter ambient clouds (not in approaching_clouds) and sort by distance, taking top 8
                ambient_clouds = [c for c in all_rain_clusters if c.get("label") not in added_labels]
                ambient_clouds.sort(key=lambda c: c.get("dist", 9999))
                
                for c in ambient_clouds[:8]:
                    lbl = c.get("label")
                    if lbl and lbl != "?" and lbl not in added_labels:
                        lock_buttons.append({"text": f"🔒 ล็อคเป้า {lbl}", "callback_data": f"lock_target_{r_lat}_{r_lng}_{lbl}"})
                        added_labels.add(lbl)
                        
                if lock_buttons:
                    # Chunk buttons into rows of 2
                    for i in range(0, len(lock_buttons), 2):
                        keyboard.append(lock_buttons[i:i+2])

        # ปุ่มสลับ Endpoint
        if actual_endpoint in ("rainbow-local", "local", "tmd-radar", "tmd-radar (kkn120)", "tmd-radar (kkn240)", "tmd-radar (skn240)"):
            keyboard.append([{"text": "🔄 สลับไปใช้ Global", "callback_data": f"switch_global_{r_lat}_{r_lng}"}])
        else:
            keyboard.append([{"text": "🔄 สลับไปใช้ Local Radar", "callback_data": f"switch_radar_{r_lat}_{r_lng}"}])

        reply_markup = {"inline_keyboard": keyboard}

        logger.info(f"Preparing to send message to chat_id={chat_id}: '{text[:80]}...'")

        await _reply(chat_id, text, message_id_to_edit, reply_markup)
            
        gif_bytes = result.get("radar_gif_bytes")
        hq_gif_bytes = result.get("radar_hq_gif_bytes")
        static_bytes = result.get("radar_static_bytes")
        tracking_bytes = result.get("radar_tracking_bytes")
        timeline_bytes = result.get("rain_timeline_bytes")
        multiframe_bytes = result.get("radar_multiframe_bytes")
        
        if show_advanced:
            if static_bytes:
                await telegram.send_telegram_photo(chat_id, static_bytes, "radar_latest.png")
                
            if timeline_bytes:
                await telegram.send_telegram_photo(chat_id, timeline_bytes, "rain_timeline.png")

            if multiframe_bytes:
                await telegram.send_telegram_photo(chat_id, multiframe_bytes, "radar_multiframe.png")
                
            if hq_gif_bytes:
                await send_telegram_raw_document(chat_id, hq_gif_bytes, "radar_nowcast_full.gif")
            
        if tracking_bytes:
            await telegram.send_telegram_photo(chat_id, tracking_bytes, "radar_tracking.png")
            
        if gif_bytes:
            await telegram.send_telegram_document(chat_id, gif_bytes, "radar_nowcast.gif")

        if show_advanced:
            advanced_data = await wm.get_advanced_alerts(lat, lng, mock_state=mock_state)
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
                
                await telegram.send_telegram_message(chat_id, adv_text)
            else:
                await telegram.send_telegram_message(chat_id, "ℹ️ ข้อมูลเตือนภัยขั้นสูง: ไม่พบประกาศเตือนภัย พายุ หรือฟ้าผ่าในระยะใกล้")

    except Exception as e:
        logger.error(f"Error processing telegram location: {e}")
        error_text = "ขออภัย ไม่สามารถดึงข้อมูลพยากรณ์ฝนได้ในขณะนี้"
        try:
            await _reply(chat_id, error_text, message_id_to_edit)
        except Exception as inner_e:
            logger.error(f"Failed to send fallback error message: {inner_e}")
