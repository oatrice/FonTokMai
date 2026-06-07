import asyncio
import logging
logging.basicConfig(level=logging.INFO)
from dotenv import load_dotenv
load_dotenv('backend/.env')
from backend.app.scheduler_tasks import fetch_tmd_radar_routine

if __name__ == "__main__":
    asyncio.run(fetch_tmd_radar_routine())
