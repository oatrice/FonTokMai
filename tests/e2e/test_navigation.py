import asyncio
from playwright.async_api import async_playwright

async def test_navigation_breadcrumbs():
    print("🧪 Testing Navigation & Breadcrumb Hierarchy...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        # 1. Check Root (/) page has link to /dashboard
        await page.goto("http://localhost:3000/")
        dashboard_nav_link = page.locator("a[href='/dashboard']")
        assert await dashboard_nav_link.count() > 0, "❌ Root page (/) is missing a button/link to /dashboard!"
        print("  ✅ Root page contains link to /dashboard")

        # 2. Check /dashboard header contains Breadcrumb (FonMaYang > System Dashboard)
        await page.goto("http://localhost:3000/dashboard")
        home_breadcrumb = page.locator("header a[href='/']")
        assert await home_breadcrumb.count() > 0, "❌ /dashboard header is missing link to /"
        
        active_breadcrumb = page.locator("header").get_by_text("System Dashboard")
        assert await active_breadcrumb.count() > 0, "❌ /dashboard header is missing 'System Dashboard' breadcrumb active badge"
        print("  ✅ /dashboard header contains clear Breadcrumb hierarchy: FonMaYang > System Dashboard")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_navigation_breadcrumbs())
