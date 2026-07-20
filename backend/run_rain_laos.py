import asyncio
import os
from app.services.weather_manager import WeatherManager

async def test():
    mgr = WeatherManager()
    res = await mgr.predict_rain(17.9142, 104.9943, mock_state="")
    print("Result keys:", res.keys())
    print("Has static_bytes:", res.get("radar_static_bytes") is not None)
    print("Has tracking_bytes:", res.get("radar_tracking_bytes") is not None)
    print("Has timeline_bytes:", res.get("rain_timeline_bytes") is not None)

if __name__ == "__main__":
    asyncio.run(test())
