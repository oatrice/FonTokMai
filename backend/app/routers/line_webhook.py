import os
import logging
from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks
from linebot.v3.webhook import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    ImageMessage,
)
from linebot.v3.webhooks import MessageEvent, LocationMessageContent, TextMessageContent

from app.dependencies import get_repo_context
from app.services.weather_manager import WeatherManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/line",
    tags=["line_webhook"]
)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "mock_token")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "mock_secret")

parser = WebhookParser(LINE_CHANNEL_SECRET)

def reply_to_line(reply_token: str, messages: list) -> bool:
    """Sends a reply to LINE containing up to 5 message objects."""
    if not messages:
        return True
    # Truncate messages to max 5 (LINE API limit)
    messages = messages[:5]
    
    # Check for mock
    if reply_token.startswith("mock") or LINE_CHANNEL_ACCESS_TOKEN == "mock_token":
        logger.info(f"[MOCK LINE REPLY] Token: {reply_token}")
        for idx, msg in enumerate(messages, 1):
            if hasattr(msg, "text"):
                logger.info(f"  Msg {idx} (Text):\n{msg.text}")
            elif hasattr(msg, "original_content_url"):
                logger.info(f"  Msg {idx} (Image URL): {msg.original_content_url}")
        return True
        
    config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
    with ApiClient(config) as api_client:
        line_bot_api = MessagingApi(api_client)
        reply_message_request = ReplyMessageRequest(
            replyToken=reply_token,
            messages=messages
        )
        line_bot_api.reply_message(reply_message_request)
    return True

async def process_line_location(user_id: str, lat: float, lng: float, title: str, reply_token: str):
    from app.routers.webhook import _build_forecast_text
    
    async with get_repo_context() as repo:
        # Save location in database with platform='line'
        await repo.save_location(
            chat_id=user_id,
            lat=lat,
            lng=lng,
            retention_type="FOREVER",
            name=title,
            platform="line"
        )
        
        # Trigger immediate prediction
        weather_manager = WeatherManager()
        mock_state = await repo.get_mock_state(user_id)
        result = await weather_manager.predict_rain(lat, lng, mock_state=mock_state, location_name=title)
        
        # Format response text
        text, actual_endpoint, eta = _build_forecast_text(result)
        
        # Confirmatory subscription prefix
        confirm_text = f"📍 บันทึกพิกัด '{title}' สำเร็จ!\nระบบจะส่งสัญญานเตือนภัยหากตรวจพบกลุ่มฝนเคลื่อนเข้าหาตัวคุณ\n\n" + text
        
        # Reply to user
        config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
        
        def _reply():
            if reply_token.startswith("mock") or LINE_CHANNEL_ACCESS_TOKEN == "mock_token":
                logger.info(f"[MOCK LINE REPLY] Reply Token: {reply_token}\nContent:\n{confirm_text}")
                return True
                
            with ApiClient(config) as api_client:
                line_bot_api = MessagingApi(api_client)
                reply_message_request = ReplyMessageRequest(
                    replyToken=reply_token,
                    messages=[TextMessage(text=confirm_text)]
                )
                line_bot_api.reply_message(reply_message_request)
            return True

        import asyncio
        await asyncio.to_thread(_reply)

async def process_line_command(user_id: str, command: str, reply_token: str):
    from app.routers.webhook import _build_forecast_text
    from app.services.notification import get_notification_service
    
    notifier = get_notification_service("line")
    parts = command.strip().split()
    cmd_name = parts[0].lower()
    
    # 1. Handle /devmock command
    if cmd_name == "/devmock":
        if len(parts) < 2:
            reply_to_line(reply_token, [TextMessage(text="ℹ️ รูปแบบการใช้งาน: /devmock [rain|clear|off]")])
            return
        state = parts[1].lower()
        if state == "off":
            state = None
        elif state not in ("rain", "clear"):
            reply_to_line(reply_token, [TextMessage(text="❌ สถานะไม่ถูกต้อง กรุณาเลือก: rain, clear, off")])
            return
            
        async with get_repo_context() as repo:
            await repo.set_mock_state(user_id, state)
        reply_to_line(reply_token, [TextMessage(text=f"✅ ตั้งค่าสถานะจำลอง (mock state) เป็น '{state or 'off'}' เรียบร้อยแล้ว")])
        return

    # 2. Handle /mylocation command
    if cmd_name == "/mylocation":
        async with get_repo_context() as repo:
            locs = await repo.get_user_locations(user_id)
        if not locs:
            reply_to_line(reply_token, [TextMessage(text="⚠️ ไม่พบพิกัดที่บันทึกไว้ กรุณาส่ง Location ให้บอทก่อนครับ")])
            return
        
        lines = ["📍 พิกัดของคุณที่บันทึกไว้:"]
        for idx, loc in enumerate(locs, 1):
            name = loc.name or "default"
            lines.append(f"{idx}. {name} ({loc.latitude}, {loc.longitude}) [{loc.retention_type}]")
        reply_to_line(reply_token, [TextMessage(text="\n".join(lines))])
        return

    # 3. Handle /rain, /rain_pro, /check, /radar, /tracking, /timeline, /nowcast commands
    if cmd_name in ("/rain", "/rain_pro", "/check", "/radar", "/tracking", "/timeline", "/nowcast"):
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
        
        if cmd_name == "/check":
            force_provider = "tmd-radar"
            
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
                chat_id=user_id,
                latitude=custom_lat,
                longitude=custom_lng,
                name=f"{custom_lat}, {custom_lng}"
            )
        else:
            async with get_repo_context() as repo:
                locs = await repo.get_user_locations(user_id)
            if not locs:
                reply_to_line(reply_token, [TextMessage(text="⚠️ ไม่พบพิกัดที่บันทึกไว้ กรุณาส่ง Location ให้บอทก่อนครับ")])
                return
                
            if target_location_name:
                for l in locs:
                    if (l.name and l.name.lower() == target_location_name) or (target_location_name == "default" and l.name is None):
                        loc = l
                        break
                if not loc:
                    available_locs = ", ".join([l.name for l in locs if l.name])
                    reply_to_line(reply_token, [TextMessage(text=f"⚠️ ไม่พบพิกัดชื่อ '{target_location_name}'\nพิกัดที่มี: {available_locs or 'default'}")])
                    return
            else:
                loc = locs[0]
                
        loc_display = loc.name.capitalize() if loc.name else "ระบบอัตโนมัติ"
        
        # Note: We skip the intermediate "⏳ กำลังตรวจสอบ..." message because replyToken can only be consumed once.
        
        async with get_repo_context() as repo:
            mock_state = await repo.get_mock_state(user_id)
            
        weather_manager = WeatherManager()
        result = await weather_manager.predict_rain(
            loc.latitude, loc.longitude,
            mock_state=mock_state,
            force_endpoint=force_provider,
            location_name=loc_display
        )
        
        text, actual_endpoint, eta_minutes = _build_forecast_text(result)
        if loc_display:
            text = f"📍 พื้นที่: {loc_display}\n\n" + text
            
        if result.get("is_outdated"):
            text = "⚠️ ยังไม่มีข้อมูลล่าสุดจากกรมอุตุฯ (TMD Radar)\nแนะนำให้เปลี่ยนไปใช้ API อื่น (เช่น Tomorrow.io หรือ Open-Meteo) แทนชั่วคราวครับ\n"
            
        if actual_endpoint == "error":
            reply_to_line(reply_token, [TextMessage(text="⚠️ ขออภัย ไม่สามารถเชื่อมต่อกับระบบพยากรณ์ฝนได้ในขณะนี้\nกรุณาลองใหม่อีกครั้งในภายหลัง")])
            return
            
        reply_messages = [TextMessage(text=text)]
        
        static_bytes = result.get("radar_static_bytes")
        tracking_bytes = result.get("radar_tracking_bytes")
        gif_bytes = result.get("radar_gif_bytes")
        timeline_bytes = result.get("rain_timeline_bytes")
        multiframe_bytes = result.get("radar_multiframe_bytes")
        
        show_advanced = (cmd_name == "/rain_pro")
        
        # Helper to upload media asynchronously and append ImageMessages
        async def _upload_and_add_msg(data, ext, mime):
            import asyncio
            url = await asyncio.to_thread(notifier._upload_media, data, mime, ext)
            if url:
                reply_messages.append(ImageMessage(original_content_url=url, preview_image_url=url))
        
        if show_advanced:
            if static_bytes:
                await _upload_and_add_msg(static_bytes, f"_{loc.name or 'default'}.png", "image/png")
            if tracking_bytes:
                await _upload_and_add_msg(tracking_bytes, f"_{loc.name or 'default'}.png", "image/png")
            if timeline_bytes:
                await _upload_and_add_msg(timeline_bytes, f"_{loc.name or 'default'}.png", "image/png")
            if multiframe_bytes:
                # Send GIF as ImageMessage for LINE
                await _upload_and_add_msg(multiframe_bytes, f"_{loc.name or 'default'}.gif", "image/gif")
        elif cmd_name in ("/rain", "/check"):
            if tracking_bytes:
                await _upload_and_add_msg(tracking_bytes, f"_{loc.name or 'default'}.png", "image/png")
            if gif_bytes:
                await _upload_and_add_msg(gif_bytes, f"_{loc.name or 'default'}.gif", "image/gif")
        elif cmd_name == "/radar":
            if static_bytes:
                await _upload_and_add_msg(static_bytes, f"_{loc.name or 'default'}.png", "image/png")
        elif cmd_name == "/tracking":
            if tracking_bytes:
                await _upload_and_add_msg(tracking_bytes, f"_{loc.name or 'default'}.png", "image/png")
        elif cmd_name == "/timeline":
            if timeline_bytes:
                await _upload_and_add_msg(timeline_bytes, f"_{loc.name or 'default'}.png", "image/png")
        elif cmd_name == "/nowcast":
            if gif_bytes:
                await _upload_and_add_msg(gif_bytes, f"_{loc.name or 'default'}.gif", "image/gif")
                
        if show_advanced:
            advanced_data = result.get("advanced_alerts", {})
            advisories = advanced_data.get("advisories", [])
            lightning = advanced_data.get("lightning", {})
            stormcells = advanced_data.get("stormcells", [])
            
            has_advisory = len(advisories) > 0
            has_lightning = bool(lightning.get("detected", False))
            has_stormcell = len(stormcells) > 0
            
            if has_advisory or has_lightning or has_stormcell:
                from app.routers.webhook import _build_advanced_text
                adv_text = _build_advanced_text(advisories, lightning, stormcells)
                reply_messages.append(TextMessage(text=adv_text))
                
        reply_to_line(reply_token, reply_messages)
        return

    # 4. Unknown Command
    reply_to_line(reply_token, [TextMessage(text=f"❓ ไม่รู้จักคำสั่ง '{cmd_name}'")])

async def handle_line_events(events, background_tasks: BackgroundTasks):
    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        
        user_id = event.source.user_id
        
        # Handle shared Location
        if isinstance(event.message, LocationMessageContent):
            lat = event.message.latitude
            lng = event.message.longitude
            title = event.message.title or "ตำแหน่งที่แชร์"
            
            logger.info(f"Processing Line location sharing: user={user_id}, lat={lat}, lng={lng}")
            background_tasks.add_task(process_line_location, user_id, lat, lng, title, event.reply_token)
        
        # Handle Text Commands
        elif isinstance(event.message, TextMessageContent):
            text = event.message.text.strip()
            if text.startswith("/"):
                logger.info(f"Processing Line text command: user={user_id}, text={text}")
                background_tasks.add_task(process_line_command, user_id, text, event.reply_token)

@router.post("/webhook")
async def line_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_line_signature: str = Header(None, alias="X-Line-Signature")
):
    if not x_line_signature:
        raise HTTPException(status_code=400, detail="Missing signature")
        
    body = await request.body()
    body_str = body.decode("utf-8")
    
    # In development mode or local requests, allow bypassing signature verification by calculating the correct signature on the fly
    is_dev = os.getenv("ENVIRONMENT", "development").lower() == "development"
    is_local = request.url.hostname in ("127.0.0.1", "localhost")
    if (is_dev or is_local) and x_line_signature == "MOCK_SIGNATURE":
        import hmac
        import hashlib
        import base64
        hash_val = hmac.new(
            LINE_CHANNEL_SECRET.encode('utf-8'),
            body,
            hashlib.sha256
        ).digest()
        x_line_signature = base64.b64encode(hash_val).decode('utf-8')
    
    try:
        events = parser.parse(body_str, x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
        
    background_tasks.add_task(handle_line_events, events, background_tasks)
    return {"status": "ok"}
