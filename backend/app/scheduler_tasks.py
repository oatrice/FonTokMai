import logging
from datetime import datetime, timedelta, timezone
from app.database import AsyncSessionLocal
from app.services.location import get_active_locations, update_last_alerted_at
from app.services.rainbow import RainbowService
from app.services.telegram import send_telegram_message

logger = logging.getLogger(__name__)

# Minimum cooldown between alerts in minutes
ALERT_COOLDOWN_MINUTES = 120

async def check_rain_and_alert():
    """
    Background job to check rain for all active locations and alert users.
    """
    logger.info("Starting proactive rain check...")
    
    async with AsyncSessionLocal() as session:
        locations = await get_active_locations(session)
        
        if not locations:
            logger.info("No active locations to check.")
            return

        rainbow_svc = RainbowService()
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        for loc in locations:
            # Check cooldown
            if loc.last_alerted_at:
                time_since_last_alert = now - loc.last_alerted_at
                if time_since_last_alert < timedelta(minutes=ALERT_COOLDOWN_MINUTES):
                    logger.debug(f"Skipping chat_id {loc.chat_id} due to cooldown.")
                    continue
            
            try:
                result = await rainbow_svc.predict_rain_by_location(loc.latitude, loc.longitude)
                predictions = result.get("predictions", [])
                
                eta_minutes = None
                if predictions:
                    try:
                        base_time = datetime.fromisoformat(predictions[0].get("time", "").replace("Z", "+00:00")).replace(tzinfo=None)
                    except Exception:
                        base_time = None
                        
                    for pred in predictions:
                        if pred.get("rain", 0) > 0:
                            if base_time:
                                try:
                                    pred_time = datetime.fromisoformat(pred.get("time", "").replace("Z", "+00:00")).replace(tzinfo=None)
                                    eta_minutes = int((pred_time - base_time).total_seconds() / 60)
                                except Exception:
                                    eta_minutes = 0
                            else:
                                eta_minutes = 0
                            break
                
                # We only alert proactively if rain is coming within 60 mins
                if eta_minutes is not None and eta_minutes <= 60:
                    if eta_minutes == 0:
                        text = "ฝนกำลังตกอยู่ที่พิกัดของคุณ ณ ขณะนี้\n"
                    else:
                        text = f"ฝนกำลังเคลื่อนมาทางทิศของคุณ จะตกหนักที่พิกัดของคุณในอีก {eta_minutes} นาที\n"
                    
                    logger.info(f"Alerting chat_id {loc.chat_id}: ETA {eta_minutes} mins")
                    
                    # Call Telegram Service
                    await send_telegram_message(loc.chat_id, text)
                    
                    # Update DB
                    await update_last_alerted_at(session, loc.chat_id)
                    
            except Exception as e:
                logger.error(f"Failed to check rain for chat_id {loc.chat_id}: {e}")
