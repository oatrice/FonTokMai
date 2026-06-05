import asyncio
import json
import time
import websockets
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
active_websockets = set()

class MockEarthquake(BaseModel):
    mag: float = 7.8
    lat: float
    lng: float
    place: str = "Mock E2E Earthquake"

@app.post("/trigger")
async def trigger_event(event: MockEarthquake):
    """Endpoint for Postman to trigger a WebSocket push"""
    timestamp_id = f"emsc_mock_{int(time.time())}"
    
    # Raw JSON payload identical to real EMSC response
    payload = {
        "action": "create",
        "data": {
            "type": "Feature",
            "properties": {
                "source_id": timestamp_id,
                "unid": timestamp_id,
                "mag": event.mag,
                "flynn_region": event.place,
                "time": "2026-06-05T12:00:00.0Z",
                "lat": event.lat,
                "lon": event.lng,
                "depth": 10.0
            }
        }
    }
    
    msg_str = json.dumps(payload)
    
    if not active_websockets:
        return {"status": "error", "message": "No backend server is connected to this Mock WebSocket!"}
        
    for ws in active_websockets:
        try:
            await ws.send(msg_str)
            print(f"📡 Broadcasted mock earthquake to connected client.")
        except Exception as e:
            print(f"❌ Failed to send: {e}")
            
    return {"status": "ok", "message": f"Broadcasted to {len(active_websockets)} connected backend(s)"}

async def mock_emsc_handler(websocket, path=None):
    """Handles incoming WebSocket connections from our FastAPI backend"""
    print("🔌 Backend Server connected to Mock EMSC Server!")
    active_websockets.add(websocket)
    try:
        # Keep connection open infinitely
        await asyncio.Future()
    except asyncio.CancelledError:
        pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        print("🔌 Backend Server disconnected.")
        active_websockets.remove(websocket)

async def start_ws_server():
    print("🚀 Starting Mock EMSC WebSocket Server on ws://localhost:8765 ...")
    server = await websockets.serve(mock_emsc_handler, "localhost", 8765)
    await server.wait_closed()

@app.on_event("startup")
async def startup_event():
    # Start the websocket server in the background alongside FastAPI
    asyncio.create_task(start_ws_server())

if __name__ == "__main__":
    print("==========================================================")
    print("E2E MOCK SERVER IS RUNNING")
    print("- WebSocket Server: ws://localhost:8765")
    print("- HTTP Trigger API: POST http://localhost:8766/trigger")
    print("==========================================================")
    uvicorn.run("mock_emsc_ws:app", host="127.0.0.1", port=8766, log_level="warning")
