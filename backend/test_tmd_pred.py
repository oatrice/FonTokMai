import asyncio
import os
import sys

# Add the backend dir to sys.path
sys.path.append("/Users/oatrice/Software-projects/FonMaYang/backend")

from app.services.weather_manager import WeatherManager

async def main():
    wm = WeatherManager()
    lat = 17.839305
    lng = 102.573027
    print(f"Testing for lat={lat}, lng={lng}")
    res = await wm._get_tmd_prediction(lat, lng)
    
    print("\nResult:")
    for k, v in res.items():
        if k not in ["radar_gif_bytes", "radar_static_bytes"]:
            print(f"{k}: {v}")
            
    # Also dump neighborhood
    from app.services.tmd_radar_processor import TMDRadarProcessor
    processor = TMDRadarProcessor(station_code="kkn240")
    frames = await processor.fetch_loop_gif_and_extract_frames()
    if frames:
        img = frames[-1]
        px, py = processor.latlng_to_pixel(lat, lng, processor.config)
        print(f"\nTarget pixel: ({px}, {py})")
        print("Neighborhood 21x21:")
        for dy in range(-10, 11):
            row = []
            for dx in range(-10, 11):
                d = processor.get_dbz_at_pixel(img, px+dx, py+dy)
                row.append(f"{int(d):02d}")
            print(" ".join(row))

if __name__ == "__main__":
    asyncio.run(main())
