import asyncio
from backend.app.database import engine, Base
from backend.app.dependencies import get_repo_context
from backend.app.models import RadarLatestCache

async def check():
    async with get_repo_context() as repo:
        cache = await repo.get_latest_radar_cache("skn240")
        if cache:
            print("Found cache!")
            print("url_t:", cache["url_t"])
            print("timestamp:", cache["timestamp"])
        else:
            print("No cache found")

asyncio.run(check())
