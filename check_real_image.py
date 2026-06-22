import asyncio
from app.services.tmd_radar_processor import TMDRadarProcessor

async def main():
    processor = TMDRadarProcessor("skn240")
    img, _, _ = await processor.get_radar_images()
    if img is None:
        print("Failed to download")
        return
    for dy in range(-15, 16):
        for dx in range(-15, 16):
            sx = 537 + dx
            sy = 349 + dy
            d = processor.get_dbz_at_pixel(img, sx, sy)
            if d >= 10.0:
                print(f"Found {d} dBZ at offset {dx}, {dy} (color: {img[sy, sx]})")
                
asyncio.run(main())
