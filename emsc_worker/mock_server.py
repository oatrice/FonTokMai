import asyncio
import websockets
import json
import os
from urllib.parse import urlparse

# Load .env file manually since python-dotenv isn't in requirements.txt
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

async def mock_emsc_server(websocket):
    print("🟢 Worker connected to our mock server!")
    
    mock_payload = {
        "action": "create",
        "data": {
            "properties": {
                "unid": "mock-ws-123",
                "mag": 7.5,
                "flynn_region": "Mock Local Test Region",
                "time": "2026-06-18T00:00:00Z",
                "lat": 13.75,
                "lon": 100.50,
                "depth": 10
            }
        }
    }
    
    loop = asyncio.get_event_loop()
    event_counter = 1
    
    while True:
        print("\n👇 Press [ENTER] to push a fake earthquake to the worker, or type 'quit' to exit.")
        user_input = await loop.run_in_executor(None, input)
        
        if user_input.lower() == 'quit':
            break
            
        print(f"🚀 Pushing fake earthquake payload (mock-test-{999 + event_counter}) to worker...")
        
        # Update the payload with a unique ID every time to bypass server deduplication
        mock_payload["data"]["properties"]["unid"] = f"mock-test-{999 + event_counter}"
        
        await websocket.send(json.dumps(mock_payload))
        event_counter += 1

async def main():
    # Read the URL from .env or default to ws://localhost:8765
    ws_url = os.getenv("EMSC_WS_URL", "ws://localhost:8765")
    parsed_url = urlparse(ws_url)
    
    host = parsed_url.hostname or "localhost"
    port = parsed_url.port or 8765

    print(f"Starting Mock EMSC WebSocket Server on ws://{host}:{port} ...")
    async with websockets.serve(mock_emsc_server, host, port):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Mock server stopped by user.")
