import asyncio
from backend.app.database import engine, Base
# Import all models to ensure they are registered with Base
from backend.app.models import UserLocation, RadarLatestCache

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('DB init done')

asyncio.run(init_db())
