import os
import sys
import asyncio
from dotenv import load_dotenv

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from app.database import AsyncSessionLocal
from app.repositories.firestore import FirestoreLocationRepository
from app.repositories.sqlite import SQLiteLocationRepository

async def migrate():
    print("🚀 Starting Migration: Firestore → Neon DB (preview/dev)...")
    
    db_url = os.getenv("DATABASE_URL")
    print(f"🔗 Target Database URL: {db_url}")

    fs_repo = FirestoreLocationRepository()
    
    # Stream all documents from Firestore user_locations collection
    docs = []
    async for doc in fs_repo.collection.stream():
        data = doc.to_dict()
        model = fs_repo._dict_to_model(data)
        docs.append(model)
        
    print(f"📦 Fetched {len(docs)} locations from Firestore.")

    if not docs:
        print("⚠️ No locations found in Firestore to migrate.")
        return

    for d in docs:
        print(f"   - chat_id={d.chat_id}, name='{d.name}', lat={d.latitude}, lng={d.longitude}, retention={d.retention_type}")

    # Insert into Neon DB
    async with AsyncSessionLocal() as session:
        sqlite_repo = SQLiteLocationRepository(session)
        migrated_count = 0
        for loc in docs:
            await sqlite_repo.save_location(
                chat_id=loc.chat_id,
                lat=loc.latitude,
                lng=loc.longitude,
                retention_type=loc.retention_type,
                name=loc.name or "default",
                platform=loc.platform or "telegram"
            )
            migrated_count += 1
            
    print(f"✅ Migration Completed! Successfully migrated {migrated_count} locations to Neon DB.")

if __name__ == "__main__":
    asyncio.run(migrate())
