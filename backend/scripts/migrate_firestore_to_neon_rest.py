import os
import sys
import asyncio
import subprocess
import httpx
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from dotenv import load_dotenv

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from app.database import AsyncSessionLocal
from app.models import UserLocation
from sqlalchemy import text

def parse_firestore_field(val_obj):
    if not val_obj or "nullValue" in val_obj:
        return None
    if "stringValue" in val_obj:
        return val_obj["stringValue"]
    if "doubleValue" in val_obj:
        return float(val_obj["doubleValue"])
    if "integerValue" in val_obj:
        return int(val_obj["integerValue"])
    if "booleanValue" in val_obj:
        return bool(val_obj["booleanValue"])
    if "timestampValue" in val_obj:
        # ISO string to datetime
        ts_str = val_obj["timestampValue"].rstrip("Z")
        return datetime.fromisoformat(ts_str)
    return None

async def migrate():
    print("🚀 Starting Migration via Firestore REST API → Neon DB (preview/dev)...")

    # Get gcloud access token
    try:
        token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    except Exception as e:
        print(f"❌ Failed to get gcloud access token: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}
    base_url = "https://firestore.googleapis.com/v1/projects/fonmayang/databases/(default)/documents/user_locations"

    documents = []
    page_token = None
    async with httpx.AsyncClient() as http:
        while True:
            params = {}
            if page_token:
                params["pageToken"] = page_token
            params["pageSize"] = 300

            resp = await http.get(base_url, headers=headers, params=params)
            if resp.status_code != 200:
                print(f"❌ Firestore REST Error ({resp.status_code}): {resp.text}")
                return

            data = resp.json()
            docs = data.get("documents", [])
            documents.extend(docs)

            page_token = data.get("nextPageToken")
            if not page_token:
                break

    print(f"📦 Fetched {len(documents)} document(s) from Firestore REST API.")

    parsed_locations = []
    for doc in documents:
        fields = doc.get("fields", {})
        chat_id = parse_firestore_field(fields.get("chat_id"))
        name = parse_firestore_field(fields.get("name")) or "default"
        platform = parse_firestore_field(fields.get("platform")) or "telegram"
        latitude = parse_firestore_field(fields.get("latitude"))
        longitude = parse_firestore_field(fields.get("longitude"))
        retention_type = parse_firestore_field(fields.get("retention_type")) or "FOREVER"
        expires_at = parse_firestore_field(fields.get("expires_at"))
        last_alerted_at = parse_firestore_field(fields.get("last_alerted_at"))
        last_alert_max_rain = parse_firestore_field(fields.get("last_alert_max_rain")) or 0.0
        tracking_mode = parse_firestore_field(fields.get("tracking_mode")) or "auto"
        locked_target_id = parse_firestore_field(fields.get("locked_target_id"))
        locked_target_cx = parse_firestore_field(fields.get("locked_target_cx"))
        locked_target_cy = parse_firestore_field(fields.get("locked_target_cy"))

        if chat_id is not None and latitude is not None and longitude is not None:
            parsed_locations.append({
                "chat_id": str(chat_id),
                "name": str(name),
                "platform": str(platform),
                "latitude": float(latitude),
                "longitude": float(longitude),
                "retention_type": str(retention_type),
                "expires_at": expires_at,
                "last_alerted_at": last_alerted_at,
                "last_alert_max_rain": float(last_alert_max_rain),
                "tracking_mode": str(tracking_mode),
                "locked_target_id": locked_target_id,
                "locked_target_cx": locked_target_cx,
                "locked_target_cy": locked_target_cy,
            })

    print(f"✨ Parsed {len(parsed_locations)} valid location record(s).")
    for loc in parsed_locations:
        print(f"   📍 chat_id={loc['chat_id']}, name='{loc['name']}', lat={loc['latitude']}, lng={loc['longitude']}, platform={loc['platform']}")

    # Insert into Neon DB
    db_url = os.getenv("DATABASE_URL")
    print(f"\n🔗 Connecting to Neon DB...")

    async with AsyncSessionLocal() as session:
        # Clear existing records first to be 100% clean
        await session.execute(text("TRUNCATE TABLE user_locations RESTART IDENTITY;"))
        await session.commit()
        print("🧹 Table 'user_locations' truncated.")

        inserted_count = 0
        for loc in parsed_locations:
            stmt = text("""
                INSERT INTO user_locations (
                    chat_id, name, platform, latitude, longitude,
                    retention_type, expires_at, last_alerted_at, last_alert_max_rain,
                    tracking_mode, locked_target_id, locked_target_cx, locked_target_cy
                ) VALUES (
                    :chat_id, :name, :platform, :latitude, :longitude,
                    :retention_type, :expires_at, :last_alerted_at, :last_alert_max_rain,
                    :tracking_mode, :locked_target_id, :locked_target_cx, :locked_target_cy
                )
            """)
            await session.execute(stmt, loc)
            inserted_count += 1

        await session.commit()

    print(f"\n🎉 Migration Complete! Successfully migrated {inserted_count} locations into Neon DB.")

if __name__ == "__main__":
    asyncio.run(migrate())
