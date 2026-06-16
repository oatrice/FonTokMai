import asyncio
import json
import logging
import httpx
import websockets
from typing import Callable, Awaitable, Any, Dict

logger = logging.getLogger(__name__)

import os

USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
EMSC_WS_URL = os.getenv("EMSC_WS_URL", "wss://www.seismicportal.eu/standing_order/websocket")

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

    Logging strategy (Cloud Logging cost optimization — Issue #69):
    - Connection/reconnection events: INFO/WARNING (kept, low frequency)
    - Per-message processing: DEBUG only (suppressed in production)
    - JSON parse errors: DEBUG (can be transient noise from EMSC)
    - Actual earthquake callbacks: INFO (important, low frequency)
    """
    logger.info("Starting EMSC Earthquake WebSocket listener...")
    _msg_count = 0  # Track message count for periodic log sampling
    while True:
        try:
            async with websockets.connect(EMSC_WS_URL) as websocket:
                logger.info("Connected to EMSC WebSocket.")
                async for message in websocket:
                    _msg_count += 1
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
                                "time": props.get("time"),  # ISO 8601 string
                                "lat": props.get("lat"),
                                "lng": props.get("lon"),
                                "depth": props.get("depth"),
                                "source": "EMSC"
                            }
                            # Log earthquake events at INFO (important, rare)
                            logger.info(
                                f"EMSC earthquake event [{action}]: "
                                f"mag={event.get('mag')}, place={event.get('place')}"
                            )
                            # Dispatch to callback in background
                            asyncio.create_task(callback(event))
                        else:
                            # Non-earthquake messages (heartbeat, ack, etc.) — DEBUG only
                            # Log every 100th message to confirm connectivity without spamming
                            if _msg_count % 100 == 0:
                                logger.debug(
                                    f"EMSC WebSocket: received {_msg_count} messages "
                                    f"(action={action!r}, last ping healthy)"
                                )
                    except json.JSONDecodeError:
                        # Downgrade from WARNING to DEBUG — transient noise, not actionable
                        logger.debug(f"EMSC: non-JSON message received (msg #{_msg_count}), skipping.")
                    except Exception as e:
                        logger.error(f"Error processing EMSC message: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.warning("EMSC WebSocket closed. Reconnecting in 5s...")
            _msg_count = 0  # Reset counter on reconnect
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"EMSC WebSocket error: {e}. Reconnecting in 10s...")
            _msg_count = 0
            await asyncio.sleep(10)

