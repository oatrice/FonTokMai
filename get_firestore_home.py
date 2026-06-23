import asyncio
from app.dependencies import get_repo_context

async def main():
    async with get_repo_context() as repo:
        locs = await repo.get_locations(6346467495)
        for loc in locs:
            print(f"Location {loc.name}: {loc.latitude}, {loc.longitude}")

asyncio.run(main())
