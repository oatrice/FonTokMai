"""
Migration script สำหรับ user_locations schema
ครอบคลุม:
  - Issue #26 : เพิ่ม last_alert_max_rain
  - Issue #9  : เพิ่ม name column (หากยังไม่มี)

รัน: python scripts/migrate_issue26.py
"""
import sqlite3
import os
import sys

DB_PATH = os.environ.get("DATABASE_URL", "fonmayang.db")

# ตัดส่วน "sqlite:///" ออกถ้ามี (SQLAlchemy-style URL)
if DB_PATH.startswith("sqlite:///"):
    DB_PATH = DB_PATH[len("sqlite:///"):]

# คอลัมน์ที่ต้องมีครบ: (ชื่อ, คำสั่ง ALTER)
REQUIRED_COLUMNS = [
    (
        "name",
        "ALTER TABLE user_locations ADD COLUMN name VARCHAR NOT NULL DEFAULT 'default'",
    ),
    (
        "last_alert_max_rain",
        "ALTER TABLE user_locations ADD COLUMN last_alert_max_rain FLOAT DEFAULT 0.0",
    ),
]

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] ไม่พบไฟล์ database: {DB_PATH}")
        print("       ตรวจสอบ DATABASE_URL environment variable หรือรันจาก directory ที่ถูกต้อง")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(user_locations)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    changed = False
    for col_name, alter_sql in REQUIRED_COLUMNS:
        if col_name in existing_columns:
            print(f"[OK] Column '{col_name}' มีอยู่แล้ว ข้าม")
        else:
            print(f"[...] กำลังเพิ่ม column '{col_name}'...")
            cursor.execute(alter_sql)
            print(f"[OK] เพิ่ม '{col_name}' เรียบร้อย")
            changed = True

    if changed:
        conn.commit()
        print("[OK] Migration commit สำเร็จ")
    else:
        print("[OK] ไม่มีอะไรต้อง migrate")

    conn.close()

if __name__ == "__main__":
    migrate()

