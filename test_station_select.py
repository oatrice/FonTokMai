import sys
import os
import asyncio
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.services.weather_manager import WeatherManager
from app.models import UserLocation

async def test():
    wm = WeatherManager()
    loc = UserLocation(chat_id=1, latitude=17.4142, longitude=104.3943, name="Home")
    # In weather_manager.py, there is a function to choose station
    # let's just see how it chooses.
    # Actually I can just grep the station selection logic.
