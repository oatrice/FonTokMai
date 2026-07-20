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
        from app.dependencies import get_http_client
        client = get_http_client()
        response = await client.get(USGS_URL, timeout=10.0)
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


