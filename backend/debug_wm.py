import asyncio
from app.services.weather_manager import WeatherManager
import logging

logging.basicConfig(level=logging.INFO)

async def test():
    wm = WeatherManager()
    prediction = await wm._get_tmd_prediction(17.4142, 104.3943, None, False)
    if prediction.get('radar_static_bytes'):
        with open('debug_pred_static.png', 'wb') as f:
            f.write(prediction['radar_static_bytes'])
        print("PNG saved to debug_pred_static.png")
    else:
        print("No radar_static_bytes returned")

if __name__ == "__main__":
    asyncio.run(test())
