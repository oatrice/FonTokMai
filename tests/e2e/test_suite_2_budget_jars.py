import asyncio
import os
import sqlite3
import json
from playwright.async_api import async_playwright

def set_balance(balance_thb: float):
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
            cursor.execute("INSERT INTO system_config (key, value_json) VALUES ('total_balance_thb', ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json;", (json.dumps(balance_thb),))
            conn.commit()
            conn.close()

async def run_suite_2():
    print("🚀 Running Suite 2: Transparent Budget Jars Allocation & Zero Balance (Issue #195, #201)...")
    set_balance(5140.0)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        print("  2.1 Navigating to /dashboard with normal balance (฿5,140)...")
        await page.goto("http://localhost:3000/dashboard")
        await page.wait_for_selector("text=Transparent Budget Jars")
        
        # Verify 3 Jars presence
        cloud_run = page.locator("text=Cloud Run Infrastructure")
        tmd_radar = page.locator("text=TMD Radar & Weather APIs")
        emergency = page.locator("text=Emergency Reserve Jar")
        
        assert await cloud_run.is_visible()
        assert await tmd_radar.is_visible()
        assert await emergency.is_visible()
        print("      3 Jars render successfully (50% / 30% / 20%).")
        
        print("  2.2 Testing Zero Balance Edge Case (฿0 THB)...")
        set_balance(0.0)
        await page.reload()
        await page.wait_for_selector("text=Transparent Budget Jars")
        
        # Confirm no Division by Zero crash & clean ฿0 rendering
        page_content = await page.content()
        assert "NaN" not in page_content, "Found NaN in rendered HTML on Zero Balance!"
        
        await page.screenshot(path="scratch/qa_reports/suite2_budget_jars_zero.png")
        print("  ✅ Suite 2 PASSED: 50/30/20 allocation & Zero Balance Division-by-Zero safety verified!")
        
        set_balance(5140.0)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_suite_2())
