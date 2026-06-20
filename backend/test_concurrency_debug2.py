import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def main():
    from app.services.weather_manager import WeatherManager
    wm = WeatherManager()
    lat, lng = 13.75, 100.5
    
    # Just run 1 task to see the actual logs!
    try:
        await wm._get_tmd_prediction(lat, lng)
    except Exception as e:
        pass
            
if __name__ == "__main__":
    asyncio.run(main())
