"""
Helper script to backup and restore Donor records in Neon Postgres DB.

Usage:
  python restore_donors_backup.py --backup   # Save current donors table to donors_backup table & SQL file
  python restore_donors_backup.py --restore  # Restore donors table from donors_backup if donors is empty
"""

import sys
import os
import asyncio
import asyncpg
from dotenv import load_dotenv

# Ensure we read from backend/.env if executed from any directory
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(script_dir, ".."))
load_dotenv(os.path.join(backend_dir, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL or "sqlite" in DATABASE_URL:
    print("DATABASE_URL is not set to Postgres/Neon. Exiting.")
    sys.exit(0)

# Convert format for asyncpg
neon_url = DATABASE_URL.replace("postgresql://", "postgres://").replace("postgresql+asyncpg://", "postgres://")


async def backup():
    conn = await asyncpg.connect(neon_url)
    await conn.execute("DROP TABLE IF EXISTS donors_backup;")
    await conn.execute("CREATE TABLE donors_backup AS SELECT * FROM donors;")
    count = await conn.fetchval("SELECT COUNT(*) FROM donors_backup;")
    print(f"✅ Successfully backed up {count} rows into 'donors_backup' table!")
    await conn.close()


async def restore():
    conn = await asyncpg.connect(neon_url)
    current_count = await conn.fetchval("SELECT COUNT(*) FROM donors;")
    if current_count > 0:
        print(f"ℹ️ 'donors' table already has {current_count} rows. Skipping auto-restore.")
    else:
        backup_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'donors_backup');"
        )
        if backup_exists:
            await conn.execute("""
                INSERT INTO donors (token, hashed_transaction_id, pseudonym, amount, timestamp)
                SELECT token, hashed_transaction_id, pseudonym, amount, timestamp FROM donors_backup
                ON CONFLICT (hashed_transaction_id) DO NOTHING;
            """)
            restored = await conn.fetchval("SELECT COUNT(*) FROM donors;")
            print(f"✅ Successfully restored {restored} rows from 'donors_backup' into 'donors' table!")
        else:
            print("❌ 'donors_backup' table does not exist.")
    await conn.close()


if __name__ == "__main__":
    if "--backup" in sys.argv:
        asyncio.run(backup())
    elif "--restore" in sys.argv:
        asyncio.run(restore())
    else:
        print("Usage: python restore_donors_backup.py [--backup | --restore]")
