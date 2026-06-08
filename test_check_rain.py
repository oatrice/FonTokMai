import asyncio
import logging
logging.basicConfig(level=logging.INFO)
from dotenv import load_dotenv
load_dotenv('backend/.env')
from backend.app.scheduler_tasks import check_rain_and_alert

if __name__ == "__main__":
    asyncio.run(check_rain_and_alert())
