from app.repositories.base import LocationRepository
from app.database import AsyncSessionLocal
import logging
from sqlalchemy.future import select
from datetime import datetime, timezone
from app.models import DisasterAlertHistory
from app.services.location import haversine_distance
from app.services.telegram import send_disaster_alert

logger = logging.getLogger(__name__)

# Radius mapping based on event type and severity
def get_impact_radius_km(event_type: str, event_data: dict) -> float:
    if event_type == "earthquake":
        mag = float(event_data.get("mag", 0))
        if mag >= 7.0:
            return 1000.0
        elif mag >= 6.0:
            return 800.0
        elif mag >= 4.5:
            return 300.0
        return 0.0 # Ignore small ones
    elif event_type == "cyclone":
        return 1000.0
    elif event_type == "fire":
        return 200.0
    return 0.0

async def process_disaster_event(repo: LocationRepository, event_type: str, event_data: dict):
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
        
    locations = await repo.get_active_locations()
    if not locations:
        return

    logger.info(f"Checking {len(locations)} active locations for event {event_id} (radius {impact_radius}km)")
    
    # Filter users within radius
    affected_users = []
    for loc in locations:
        dist = haversine_distance(loc.latitude, loc.longitude, lat, lng)
        if dist <= impact_radius:
            affected_users.append((loc, dist))

    logger.info(f"Found {len(affected_users)} affected users for event {event_id}")
            
    if not affected_users:
        return

    # Check alert history using repository
    alerted_count = 0
    for loc, dist in affected_users:
        if await repo.has_disaster_alert_been_sent(loc.chat_id, event_id):
            continue
            
        try:
            # We add 'distance_km' to event_data for the message
            event_data_with_dist = event_data.copy()
            event_data_with_dist["distance_km"] = dist
            
            await send_disaster_alert(loc.chat_id, event_type, event_data_with_dist, loc.name)
            await repo.mark_disaster_alert_sent(loc.chat_id, event_id, event_type)
            alerted_count += 1
            
        except Exception as e:
            logger.error(f"Failed to send {event_type} alert to {loc.chat_id}: {e}")
            
    if alerted_count > 0:
        logger.info(f"Alerted {alerted_count} users for {event_type} {event_id}")
