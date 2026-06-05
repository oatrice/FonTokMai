import asyncio
import json
import logging
import httpx
import websockets
from typing import Callable, Awaitable, Any, Dict

logger = logging.getLogger(__name__)

USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
EMSC_WS_URL = "wss://www.seismicportal.eu/standing_order/websocket"

async def fetch_usgs_geojson() -> list[Dict[str, Any]]:
    """Fetch the latest earthquakes from USGS GeoJSON feed (past hour)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(USGS_URL)
            response.raise_for_status()
            data = response.json()
            
            events = []
            for feature in data.get("features", []):
                props = feature.get("properties", {})
                geom = feature.get("geometry", {})
                
                coords = geom.get("coordinates", [0, 0, 0]) # lon, lat, depth
                
                events.append({
                    "id": feature.get("id"),
                    "mag": props.get("mag"),
                    "place": props.get("place"),
                    "time": props.get("time"),
                    "lat": coords[1] if len(coords) >= 2 else 0.0,
                    "lng": coords[0] if len(coords) >= 2 else 0.0,
                    "depth": coords[2] if len(coords) >= 3 else 0.0,
                    "source": "USGS"
                })
            return events
    except Exception as e:
        logger.error(f"Error fetching USGS GeoJSON: {e}")
        return []

async def start_emsc_websocket(callback: Callable[[Dict[str, Any]], Awaitable[None]]):
    """
    Connect to EMSC websocket and listen for real-time earthquake push notifications.
    Calls `callback(event)` for each earthquake.
    """
    logger.info("Starting EMSC Earthquake WebSocket listener...")
    while True:
        try:
            async with websockets.connect(EMSC_WS_URL) as websocket:
                logger.info("Connected to EMSC WebSocket.")
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        action = data.get("action")
                        if action == "create" or action == "update":
                            msg = data.get("data", {})
                            props = msg.get("properties", {})
                            
                            event = {
                                "id": props.get("unid", props.get("source_id")),
                                "mag": props.get("mag"),
                                "place": props.get("flynn_region"),
                                "time": props.get("time"), # ISO 8601 string
                                "lat": props.get("lat"),
                                "lng": props.get("lon"),
                                "depth": props.get("depth"),
                                "source": "EMSC"
                            }
                            # Dispatch to callback in background
                            asyncio.create_task(callback(event))
                    except json.JSONDecodeError:
                        logger.warning("Failed to decode EMSC message")
                    except Exception as e:
                        logger.error(f"Error processing EMSC message: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.warning("EMSC WebSocket closed. Reconnecting in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"EMSC WebSocket error: {e}. Reconnecting in 10s...")
            await asyncio.sleep(10)
