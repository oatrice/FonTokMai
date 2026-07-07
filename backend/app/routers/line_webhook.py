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
)
from linebot.v3.webhooks import MessageEvent, LocationMessageContent

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
