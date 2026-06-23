import asyncio
from app.services.weather_manager import WeatherManager
import logging
logging.basicConfig(level=logging.DEBUG)

async def test():
    wm = WeatherManager()
    prediction = await wm._get_tmd_prediction(17.4142, 104.3943, None, False)
    print(f"DEBUG_LOCATION: prediction={prediction}")

if __name__ == "__main__":
    asyncio.run(test())
