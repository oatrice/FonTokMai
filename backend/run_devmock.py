import asyncio
from app.routers.webhook_devmock import handle_devmock_command

async def test():
    print("Testing /devmock off")
    await handle_devmock_command(6346467495, "/devmock off")
    print("Done")

if __name__ == "__main__":
    asyncio.run(test())
