import asyncio
import os
import sys
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://neondb_owner:npg_sjZmtv4aOE3f@ep-silent-salad-azkhjran-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?ssl=require"
)

# Clean/format connection string for asyncpg
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
parsed = urlparse(DATABASE_URL)
if parsed.query:
    query_params = parse_qs(parsed.query)
    query_params.pop("channel_binding", None)
    has_sslmode = query_params.pop("sslmode", None)
    if has_sslmode and "ssl" not in query_params:
        ssl_val = has_sslmode[0] if isinstance(has_sslmode, list) else has_sslmode
        query_params["ssl"] = ["require" if ssl_val in ("require", "verify-ca", "verify-full") else ssl_val]
    new_query = urlencode(query_params, doseq=True)
    DATABASE_URL = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

async def seed_data():
    print(f"🌱 Connecting to Neon Database...")
    engine = create_async_engine(
        DATABASE_URL, 
        connect_args={
            "prepared_statement_cache_size": 0, 
            "statement_cache_size": 0
        }
    )
    
    async with engine.begin() as conn:
        # 1. Initialize Tables from Models
        from app.models import Base
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables ensured.")

        # 2. Seed Mock Donors
        await conn.execute(text("""
            INSERT INTO donors (token, hashed_transaction_id, pseudonym, amount, timestamp)
            VALUES 
                ('token_dev_001', 'hash_dev_001', 'Dev Supporter Alpha', 500.0, NOW()),
                ('token_dev_002', 'hash_dev_002', 'Beta Operator', 250.0, NOW()),
                ('token_dev_003', 'hash_dev_003', 'Ecosystem Guardian', 1000.0, NOW())
            ON CONFLICT (hashed_transaction_id) DO NOTHING;
        """))
        print("✅ Mock Donors seeded.")

        # 3. Seed Mock User Locations
        await conn.execute(text("""
            INSERT INTO user_locations (chat_id, name, platform, latitude, longitude, retention_type, tracking_mode)
            VALUES 
                ('6346467495', 'Bangkok Central', 'telegram', 13.7563, 100.5018, 'FOREVER', 'auto'),
                ('6346467495', 'Chiang Mai Station', 'telegram', 18.7883, 98.9853, 'TWO_MONTHS', 'auto')
            ON CONFLICT DO NOTHING;
        """))
        print("✅ Mock User Locations seeded.")

        # 4. Seed Mock API Reliability Metrics
        await conn.execute(text("""
            INSERT INTO api_reliability (endpoint, total_queries, false_alarms, accuracy_score)
            VALUES 
                ('xweather', 150, 3, 0.98),
                ('tomorrow', 140, 5, 0.96),
                ('rainbow-local', 200, 2, 0.99)
            ON CONFLICT (endpoint) DO NOTHING;
        """))
        print("✅ Mock API Reliability metrics seeded.")

    await engine.dispose()
    print("🎉 Seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_data())
