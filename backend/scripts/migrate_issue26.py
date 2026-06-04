"""
Migration script สำหรับ Issue #26: Smart Cooldown
เพิ่มคอลัมน์ last_alert_max_rain ในตาราง user_locations

รัน: python scripts/migrate_issue26.py
"""
import sqlite3
import os
import sys

DB_PATH = os.environ.get("DATABASE_URL", "fonmayang.db")

# ตัดส่วน "sqlite:///" ออกถ้ามี (SQLAlchemy-style URL)
if DB_PATH.startswith("sqlite:///"):
    DB_PATH = DB_PATH[len("sqlite:///"):]

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] ไม่พบไฟล์ database: {DB_PATH}")
        print("       ตรวจสอบ DATABASE_URL environment variable หรือรันจาก directory ที่ถูกต้อง")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ตรวจสอบว่า column มีอยู่แล้วหรือยัง
    cursor.execute("PRAGMA table_info(user_locations)")
    columns = [row[1] for row in cursor.fetchall()]

    if "last_alert_max_rain" in columns:
        print("[OK] Column 'last_alert_max_rain' มีอยู่แล้ว ไม่ต้อง migrate")
    else:
        print("[...] กำลังเพิ่ม column 'last_alert_max_rain'...")
        cursor.execute(
            "ALTER TABLE user_locations ADD COLUMN last_alert_max_rain FLOAT DEFAULT 0.0"
        )
        conn.commit()
        print("[OK] Migration สำเร็จ! เพิ่ม 'last_alert_max_rain FLOAT DEFAULT 0.0' เรียบร้อย")

    conn.close()

if __name__ == "__main__":
    migrate()
