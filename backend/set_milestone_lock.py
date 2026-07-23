import sys
import os
import json
import sqlite3

def set_milestone_lock(is_locked: bool):
    db_paths = [
        "/Users/oatrice/Software Project/FonMaYang/fonmayang.db",
        "/Users/oatrice/Software Project/FonMaYang/backend/fonmayang.db",
        "/Users/oatrice/Software Project/FonMaYang/.worktrees/frontend-squad/backend/fonmayang.db",
    ]
    
    val_json = json.dumps("true" if is_locked else "false")
    
    for db_path in db_paths:
        if not os.path.exists(os.path.dirname(db_path)):
            continue
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key VARCHAR NOT NULL PRIMARY KEY,
                value_json TEXT NOT NULL
            )
        """)
        cursor.execute("""
            INSERT INTO system_config (key, value_json) VALUES ('milestone_lock', ?)
            ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json
        """, (val_json,))
        conn.commit()
        conn.close()
        print(f"✅ Updated {db_path}: milestone_lock = {val_json}")

if __name__ == "__main__":
    lock_val = True
    if len(sys.argv) > 1 and sys.argv[1].lower() in ["false", "0", "off", "unlock"]:
        lock_val = False
    set_milestone_lock(lock_val)
