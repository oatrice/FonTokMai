import asyncio
import json
import logging
import os
import requests
import websockets
from websockets.exceptions import ConnectionClosed

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("emsc_worker")

# Load .env file manually for local development (systemd does this automatically in prod)
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

# Configuration
EMSC_WS_URL = os.getenv("EMSC_WS_URL", "wss://www.seismicportal.eu/standing_order/websocket")
FONMAYANG_API_URL = os.getenv("FONMAYANG_API_URL", "http://localhost:8000")
INTERNAL_WEBHOOK_SECRET = os.getenv("INTERNAL_WEBHOOK_SECRET", "dev_secret")

def forward_event(event: dict):
    """Forward the parsed earthquake event to the main Cloud Run API."""
    url = f"{FONMAYANG_API_URL.rstrip('/')}/api/v1/internal/emsc-webhook"
    headers = {
        "Content-Type": "application/json",
        "X-Internal-Secret": INTERNAL_WEBHOOK_SECRET
    }
    
    try:
        response = requests.post(url, json=event, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully forwarded event {event.get('id')} to {url}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to forward event {event.get('id')}: {e}")

async def start_worker():
    """Connect to EMSC websocket and listen for real-time earthquake push notifications."""
    logger.info(f"Starting EMSC Earthquake WebSocket listener on VM...")
    logger.info(f"Forwarding events to: {FONMAYANG_API_URL}")
    
    _msg_count = 0
    while True:
        try:
            async with websockets.connect(EMSC_WS_URL) as websocket:
                logger.info("Connected to EMSC WebSocket.")
                async for message in websocket:
                    _msg_count += 1
                    try:
                        data = json.loads(message)
                        action = data.get("action")
                        if action in ("create", "update"):
                            msg = data.get("data", {})
                            props = msg.get("properties", {})

                            event = {
                                "id": props.get("unid", props.get("source_id")),
                                "mag": props.get("mag"),
                                "place": props.get("flynn_region"),
                                "time": props.get("time"),
                                "lat": props.get("lat"),
                                "lng": props.get("lon"),
                                "depth": props.get("depth"),
                                "source": "EMSC"
                            }
                            logger.info(f"EMSC earthquake event [{action}]: mag={event.get('mag')}, place={event.get('place')}")
                            
                            # Forward event in a separate thread so we don't block the asyncio event loop
                            asyncio.create_task(asyncio.to_thread(forward_event, event))
                            
                        else:
                            if _msg_count % 100 == 0:
                                logger.debug(f"EMSC WebSocket: received {_msg_count} messages (action={action!r}, last ping healthy)")
                    except json.JSONDecodeError:
                        logger.debug(f"EMSC: non-JSON message received (msg #{_msg_count}), skipping.")
                    except Exception as e:
                        logger.error(f"Error processing EMSC message: {e}")
        except ConnectionClosed:
            logger.warning("EMSC WebSocket closed. Reconnecting in 5s...")
            _msg_count = 0
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"EMSC WebSocket error: {e}. Reconnecting in 10s...")
            _msg_count = 0
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(start_worker())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")
