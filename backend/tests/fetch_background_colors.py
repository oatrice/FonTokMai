import asyncio
import cv2
import numpy as np
import httpx
from app.services.tmd_radar_processor import TMDRadarProcessor
from PIL import Image
import io

async def main():
    url = "https://weather.tmd.go.th/kkn/kkn120_latest.gif"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
    
    if r.status_code != 200:
        print("Failed to download")
        return
        
    img = np.array(Image.open(io.BytesIO(r.content)).convert("RGB"))
    
    # Let's count the most frequent colors in the image
    # The map background should be very frequent
    colors, counts = np.unique(img.reshape(-1, 3), axis=0, return_counts=True)
    
    # Sort by count
    sorted_idx = np.argsort(-counts)
    
    print("Top 20 most frequent colors:")
    for i in range(20):
        c = colors[sorted_idx[i]]
        count = counts[sorted_idx[i]]
        print(f"RGB: {c}, count: {count}")

if __name__ == '__main__':
    asyncio.run(main())
