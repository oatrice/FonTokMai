import os
import sys
import asyncio
import sqlite3

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

CHAT_ID = "6346467495"
TARGET_LAT = 17.874829834
TARGET_LNG = 102.740330372
LOCATION_NAME = "Nong Khai House"

async def migrate_firestore():
    print("Checking Firestore...")
    import firebase_admin
    from firebase_admin import credentials, firestore_async
    
    if not firebase_admin._apps:
        try:
            cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if cred_path and os.path.exists(cred_path):
                try:
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                except Exception:
                    # Fallback to Application Default Credentials if Certificate fails
                    cred = credentials.ApplicationDefault()
                    firebase_admin.initialize_app(cred)
            else:
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred)
        except Exception as e:
            print(f"Could not initialize Firestore client: {e}")
            return
                
    db = firestore_async.client()
    collection = db.collection("user_locations")
    
    # 1. Save new location "Nong Khai House"
    new_doc_id = f"{CHAT_ID}_{LOCATION_NAME}"
    doc_ref = collection.document(new_doc_id)
    await doc_ref.set({
        "chat_id": CHAT_ID,
        "name": LOCATION_NAME,
        "latitude": TARGET_LAT,
        "longitude": TARGET_LNG,
        "retention_type": "FOREVER",
        "expires_at": None,
        "platform": "telegram"
    })
    print(f"[Firestore] Registered: {LOCATION_NAME} ({TARGET_LAT}, {TARGET_LNG})")
    
    # 2. Delete stale coordinates ("home" at 17.8725, 102.743)
    stale_doc_id = f"{CHAT_ID}_home"
    stale_ref = collection.document(stale_doc_id)
    doc = await stale_ref.get()
    if doc.exists:
        await stale_ref.delete()
        print(f"[Firestore] Deleted stale coordinates: {stale_doc_id}")
    else:
        print(f"[Firestore] No stale coordinates found under {stale_doc_id}")

def migrate_sqlite():
    db_path = os.environ.get("DATABASE_URL", "fonmayang.db")
    if db_path.startswith("sqlite:///"):
        db_path = db_path[len("sqlite:///"):]
        
    if not os.path.exists(db_path):
        print(f"SQLite DB file {db_path} not found. Skipping SQLite.")
        return
        
    print(f"Checking SQLite at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_locations';")
    if not cursor.fetchone():
        print("Table 'user_locations' does not exist in SQLite. Skipping.")
        conn.close()
        return

    # Delete existing "Nong Khai House" if any to prevent duplicates
    cursor.execute("DELETE FROM user_locations WHERE chat_id = ? AND name = ?", (CHAT_ID, LOCATION_NAME))
    
    # Insert new location
    cursor.execute("""
        INSERT INTO user_locations (chat_id, name, latitude, longitude, retention_type, expires_at, platform)
        VALUES (?, ?, ?, ?, ?, NULL, ?)
    """, (CHAT_ID, LOCATION_NAME, TARGET_LAT, TARGET_LNG, "FOREVER", "telegram"))
    print(f"[SQLite] Registered: {LOCATION_NAME} ({TARGET_LAT}, {TARGET_LNG})")
    
    # Delete stale location
    cursor.execute("DELETE FROM user_locations WHERE chat_id = ? AND name = ?", (CHAT_ID, "home"))
    print(f"[SQLite] Deleted stale coordinates 'home' for chat_id={CHAT_ID}")
    
    conn.commit()
    conn.close()

async def main():
    backend = os.getenv("STORAGE_BACKEND", "sqlite").lower()
    if backend == "firestore":
        await migrate_firestore()
    migrate_sqlite()
    print("Migration completed!")

if __name__ == "__main__":
    asyncio.run(main())
