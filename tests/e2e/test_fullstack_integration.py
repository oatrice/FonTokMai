import asyncio
import os
import sqlite3
import json
from playwright.async_api import async_playwright

def set_db_milestone_lock(is_locked: bool):
    val_json = json.dumps("true" if is_locked else "false")
    db_paths = [
        "/Users/oatrice/Software Project/FonMaYang/fonmayang.db",
        "/Users/oatrice/Software Project/FonMaYang/backend/fonmayang.db",
        "/Users/oatrice/Software Project/FonMaYang/.worktrees/frontend-squad/backend/fonmayang.db",
    ]
    for db_path in db_paths:
        if os.path.exists(os.path.dirname(db_path)):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS system_config (key VARCHAR PRIMARY KEY, value_json TEXT);")
            cursor.execute("INSERT INTO system_config (key, value_json) VALUES ('milestone_lock', ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json;", (val_json,))
            conn.commit()
            conn.close()

async def run_fullstack_integration_test():
    print("🚀 Starting Full-Stack (Frontend + Backend) Integration Test...")
    
    # 1. Reset DB to unlocked state
    set_db_milestone_lock(False)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()
        
        # 2. Navigate to Frontend Dashboard
        print("🌐 Step 1: Navigating to Frontend UI (http://localhost:3000/dashboard)...")
        response = await page.goto("http://localhost:3000/dashboard")
        assert response.status == 200, f"Frontend returned status {response.status}"
        
        # 3. Verify Frontend renders data fetched from Backend API
        print("🔍 Step 2: Verifying Frontend renders Backend API data...")
        await page.wait_for_selector("text=System Dashboard")
        await page.wait_for_selector("text=ACCEPTING DONATIONS")
        
        # 4. Trigger State Change in Backend DB
        print("⚡ Step 3: Triggering Donation Lock in Backend SQLite DB...")
        set_db_milestone_lock(True)
        
        # 5. Reload Frontend & Verify UI updates dynamically
        print("🔄 Step 4: Verifying Frontend UI reflects Backend state change...")
        await page.reload()
        await page.wait_for_selector("text=DONATION LOCKED")
        
        locked_badge = page.locator("text=DONATION LOCKED")
        assert await locked_badge.is_visible(), "DONATION LOCKED badge is not visible on UI!"
        
        alert_box = page.locator("text=Donation Lock Active")
        assert await alert_box.is_visible(), "Donation Lock alert box is not visible on UI!"
        
        print("✅ FULL-STACK INTEGRATION TEST PASSED 100%!")
        print("   - Frontend (Next.js :3000) ◄──► Backend (FastAPI :8000) ◄──► Database (SQLite)")
        
        # Reset DB back to unlocked
        set_db_milestone_lock(False)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_fullstack_integration_test())
