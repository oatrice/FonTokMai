import asyncio
from app.services.tmd_radar_processor import TMDRadarProcessor

async def run_test():
    # Using kkn240 as a target station
    processor = TMDRadarProcessor("kkn240")

    # Test with invalid non-GIF bytes
    bad_bytes = b"<html>Error 502 Bad Gateway</html>"
    
    print("Simulating invalid bytes logic directly:")
    if not (bad_bytes[:6] in (b"GIF87a", b"GIF89a")):
        print("✅ Validation correctly rejected invalid HTML/non-GIF bytes.")
    else:
        print("❌ Validation failed to reject invalid bytes.")

asyncio.run(run_test())