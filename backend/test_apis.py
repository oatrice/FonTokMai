import asyncio
from app.services.rainviewer import RainViewerService
from app.services.rainbow import RainbowService

async def main():
    print("--- Testing RainViewer ---")
    rainviewer = RainViewerService()
    try:
        rv_metadata = await rainviewer.get_current_radar_metadata()
        print(f"Result: {rv_metadata}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Testing Rainbow API ---")
    rainbow = RainbowService()
    try:
        # Sakon Nakhon coordinates
        rb_predictions = await rainbow.predict_rain_by_location(17.1664, 104.1486)
        print(f"Result: {rb_predictions}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
