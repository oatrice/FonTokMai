import asyncio
import os
from playwright.async_api import async_playwright

async def test_navigation_red():
    print("🧪 [RED PHASE] Testing Navigation between Root (/) and Dashboard (/dashboard)...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        # 1. Check Root (/) page has link to /dashboard
        await page.goto("http://localhost:3000/")
        dashboard_nav_link = page.locator("nav a[href='/dashboard'], header a[href='/dashboard']")
        assert await dashboard_nav_link.count() > 0, "❌ Root page (/) is missing a button/link to /dashboard!"
        print("  ✅ Root page contains /dashboard link")

        # 2. Check /dashboard header has active indicator and logo link back to /
        await page.goto("http://localhost:3000/dashboard")
        root_logo_link = page.locator("header a[href='/']")
        assert await root_logo_link.count() > 0, "❌ /dashboard page logo is missing link to /"
        print("  ✅ /dashboard header contains logo link to /")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_navigation_red())
