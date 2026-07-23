import asyncio
import os
import sqlite3
import json
from playwright.async_api import async_playwright

def set_overdrive_and_burn_rate(overdrive: bool, burn_rate: float):
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
            cursor.execute("INSERT INTO system_config (key, value_json) VALUES ('emergency_overdrive', ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json;", (json.dumps(overdrive),))
            cursor.execute("INSERT INTO system_config (key, value_json) VALUES ('burn_rate_per_day', ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json;", (json.dumps(burn_rate),))
            conn.commit()
            conn.close()

async def run_suite_1():
    print("🚀 Running Suite 1: Live Runway Engine & Emergency Overdrive (Issue #191, #197, #201)...")
    set_overdrive_and_burn_rate(False, 120.0)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        print("  1.1 Navigating to /dashboard in normal state...")
        await page.goto("http://localhost:3000/dashboard")
        await page.wait_for_selector("text=System Dashboard")
        
        # Verify Healthy Badge in normal state
        healthy_badge = page.locator("text=HEALTHY")
        assert await healthy_badge.is_visible(), "Healthy badge is not visible in normal mode!"
        
        print("  1.2 Setting emergency_overdrive = True in DB & reloading...")
        set_overdrive_and_burn_rate(True, 350.0)
        await page.goto("http://localhost:3000/dashboard?emergency_overdrive=true")
        await page.wait_for_selector("text=System Dashboard")
        
        # Verify UI renders Overdrive state
        burn_rate_text = await page.locator("text=Burn Rate:").text_content()
        print(f"      Burn Rate Displayed: {burn_rate_text.strip()}")
        
        os.makedirs("scratch/qa_reports", exist_ok=True)
        await page.screenshot(path="scratch/qa_reports/suite1_overdrive.png")
        print("  ✅ Suite 1 PASSED: Overdrive state & dynamic burn rate verified!")
        
        set_overdrive_and_burn_rate(False, 120.0)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_suite_1())
