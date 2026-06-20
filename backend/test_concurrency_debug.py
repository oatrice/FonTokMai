import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def main():
    from app.services.weather_manager import WeatherManager
    wm = WeatherManager()
    
    # พิกัดหนองคาย (17.8785, 102.7420) ที่อยู่ในรัศมีเรดาร์ skn240
    lat, lng = 17.8785, 102.7420
    
    print("Sending 15 concurrent requests...")
    tasks = [wm._get_tmd_prediction(lat, lng) for _ in range(15)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successes = sum(1 for r in results if not isinstance(r, Exception))
    errors = sum(1 for r in results if isinstance(r, Exception))
    print(f"Done! Success: {successes}, Errors: {errors}")
    
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            print(f"Task {i} error: {repr(r)}")
            
if __name__ == "__main__":
    asyncio.run(main())
