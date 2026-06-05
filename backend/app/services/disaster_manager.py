import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
from app.models import UserLocation, DisasterAlertHistory
from app.services.location import get_active_locations, haversine_distance
from app.services.telegram import send_disaster_alert

logger = logging.getLogger(__name__)

# Radius mapping based on event type and severity
def get_impact_radius_km(event_type: str, event_data: dict) -> float:
    if event_type == "earthquake":
        mag = float(event_data.get("mag", 0))
        if mag >= 6.0:
            return 300.0
        elif mag >= 4.5:
            return 100.0
        return 0.0 # Ignore small ones
    elif event_type == "cyclone":
        return 500.0
    elif event_type == "fire":
        return 50.0
    return 0.0

async def process_disaster_event(session: AsyncSession, event_type: str, event_data: dict):
    """
    Process a disaster event, match it against user locations, and send alerts.
    event_data should have: id, lat, lng, and type-specific fields.
    """
    event_id = str(event_data.get("id"))
    lat = float(event_data.get("lat", 0))
    lng = float(event_data.get("lng", 0))
    
    impact_radius = get_impact_radius_km(event_type, event_data)
    if impact_radius <= 0:
        return # Skip minor events
        
    locations = await get_active_locations(session)
    if not locations:
        return

    # Filter users within radius
    affected_users = []
    for loc in locations:
        dist = haversine_distance(loc.latitude, loc.longitude, lat, lng)
        if dist <= impact_radius:
            affected_users.append((loc, dist))
            
    if not affected_users:
        return

    # Check alert history
    # To optimize, we can fetch all chat_ids that already received this event_id
    query = select(DisasterAlertHistory.chat_id).where(
        DisasterAlertHistory.event_id == event_id
    )
    result = await session.execute(query)
    already_alerted_chats = set(result.scalars().all())
    
    # Send alerts to new users
    new_alerts_history = []
    for loc, dist in affected_users:
        if loc.chat_id in already_alerted_chats:
            continue
            
        try:
            # We add 'distance_km' to event_data for the message
            event_data_with_dist = event_data.copy()
            event_data_with_dist["distance_km"] = dist
            
            await send_disaster_alert(loc.chat_id, event_type, event_data_with_dist, loc.name)
            
            new_alerts_history.append(
                DisasterAlertHistory(
                    chat_id=loc.chat_id,
                    event_id=event_id,
                    event_type=event_type,
                    alerted_at=datetime.now(timezone.utc).replace(tzinfo=None)
                )
            )
        except Exception as e:
            logger.error(f"Failed to send {event_type} alert to {loc.chat_id}: {e}")
            
    if new_alerts_history:
        session.add_all(new_alerts_history)
        await session.commit()
        logger.info(f"Alerted {len(new_alerts_history)} users for {event_type} {event_id}")
