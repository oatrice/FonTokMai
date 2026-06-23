import asyncio
from app.services.tmd_radar_processor import TMDRadarProcessor

async def test():
    processor = TMDRadarProcessor("skn240")
    lat = 17.4142
    lng = 104.3943
    x, y = processor.latlng_to_pixel(lat, lng, is_loop=True)
    print(f"Kusuman (17.4142, 104.3943) mapped to X={x}, Y={y} (Loop)")

if __name__ == "__main__":
    asyncio.run(test())
