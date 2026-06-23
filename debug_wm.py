import asyncio
from backend.app.services.weather_manager import WeatherManager
import logging
import cv2

logging.basicConfig(level=logging.INFO)

async def test():
    wm = WeatherManager()
    prediction = await wm._get_tmd_prediction(17.4142, 104.3943, None, False)
    print(prediction)
    # save prediction image
    if prediction.get('radar_tracking_bytes'):
        with open('debug_pred.gif', 'wb') as f:
            f.write(prediction['radar_tracking_bytes'])

if __name__ == "__main__":
    asyncio.run(test())
