import argparse
import asyncio
import time
import sys
from dotenv import load_dotenv
load_dotenv()
from app.dependencies import get_repo_context
from app.services.disaster_manager import process_disaster_event

async def trigger_custom_event(repo, disaster_type, lat, lng, mag=7.0, name="Custom Mock Disaster"):
    timestamp = int(time.time())
    event_id = f"custom_mock_{timestamp}"
    
    event_data = {
        "id": event_id,
        "lat": lat,
        "lng": lng,
    }
    
    if disaster_type == "earthquake":
        event_data["mag"] = mag
        event_data["place"] = name
    elif disaster_type == "cyclone":
        event_data["name"] = name
        event_data["category"] = "Cat 4"
    elif disaster_type == "fire":
        event_data["name"] = name
        
    print(f"👉 Triggering custom {disaster_type} at lat={lat}, lng={lng}...")
    await process_disaster_event(repo, disaster_type, event_data)
    print("✅ Custom event dispatched! Check Telegram.")

async def trigger_default_mocks(repo, locations):
    # Use timestamp to ensure unique IDs, bypassing the DisasterAlertHistory block
    timestamp = int(time.time())
    
    # We will create mock events placed slightly offset from the first user's location
    # so that it falls within the warning radius
    target_lat = locations[0].latitude
    target_lng = locations[0].longitude
    
    # 1. Mock Earthquake (Mag 7.5, Radius: 300km)
    print(f"👉 Triggering Mock Earthquake...")
    eq_event = {
        "id": f"mock_eq_{timestamp}",
        "mag": 7.5,
        "place": "Mock Earthquake Zone (Test)",
        "lat": target_lat + 0.5,  # ~50-60km away
        "lng": target_lng + 0.5,
    }
    await process_disaster_event(repo, "earthquake", eq_event)
    await asyncio.sleep(2) # brief pause
    
    # 2. Mock Cyclone (Radius: 500km)
    print(f"👉 Triggering Mock Cyclone...")
    cy_event = {
        "id": f"mock_cy_{timestamp}",
        "name": "Typhoon Mockingbird",
        "category": "Cat 4",
        "lat": target_lat + 2.0,  # ~220km away
        "lng": target_lng + 2.0,
    }
    await process_disaster_event(repo, "cyclone", cy_event)
    await asyncio.sleep(2)
    
    # 3. Mock Fire (Radius: 50km)
    print(f"👉 Triggering Mock Fire...")
    fire_event = {
        "id": f"mock_fire_{timestamp}",
        "name": "Mock Forest Fire",
        "lat": target_lat + 0.1,  # ~11km away
        "lng": target_lng + 0.1,
    }
    await process_disaster_event(repo, "fire", fire_event)
    
    print("✅ All default mock events processed! Please check your Telegram.")

async def main():
    parser = argparse.ArgumentParser(description="Trigger mock disaster events.")
    parser.add_argument("--type", choices=["earthquake", "cyclone", "fire"], help="Type of custom disaster to trigger")
    parser.add_argument("--lat", type=float, help="Latitude for the custom disaster")
    parser.add_argument("--lng", type=float, help="Longitude for the custom disaster")
    parser.add_argument("--mag", type=float, default=7.0, help="Magnitude (only used if type is earthquake)")
    parser.add_argument("--name", type=str, default="Custom Manual Disaster", help="Name or place of the disaster")
    args = parser.parse_args()

    async with get_repo_context() as repo:
        locations = await repo.get_active_locations()
        if not locations:
            print("❌ No active user locations found in the database. Cannot send Telegram mock alerts.")
            return
            
        print(f"✅ Found {len(locations)} active locations.")
        
        # If user passed custom arguments, fire that specific event
        if args.type and args.lat is not None and args.lng is not None:
            await trigger_custom_event(repo, args.type, args.lat, args.lng, args.mag, args.name)
        # Otherwise run the default bundle
        elif not args.type and args.lat is None and args.lng is None:
            await trigger_default_mocks(repo, locations)
        else:
            print("❌ Please provide --type, --lat, and --lng together to trigger a custom event.")
            parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
