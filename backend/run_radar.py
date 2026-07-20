import asyncio
from dotenv import load_dotenv
load_dotenv()

from app.scheduler_tasks import fetch_tmd_radar_routine

async def test():
    print("Starting parallel fetch...")
    await fetch_tmd_radar_routine()
    print("Done!")

asyncio.run(test())