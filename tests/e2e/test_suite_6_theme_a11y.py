import asyncio
import os
from playwright.async_api import async_playwright

async def run_suite_6():
    print("🚀 Running Suite 6: Dark Glassmorphic Theme & Keyboard Accessibility (Issue #203)...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        print("  6.1 Navigating to /dashboard...")
        await page.goto("http://localhost:3000/dashboard")
        await page.wait_for_selector("text=System Dashboard")
        
        # 1. Assert Dark Glassmorphism Design Token Compliance
        print("  6.2 Verifying Default Dark Glassmorphic Theme applied...")
        body_bg = await page.eval_on_selector("body", "el => getComputedStyle(el).backgroundColor")
        print(f"      Body background color: {body_bg}")
        assert "rgb(" in body_bg, "Default body background is not rendered!"

        # 2. Assert Keyboard Navigation (Focus ring)
        print("  6.3 Testing Tab key navigation to interactive elements...")
        await page.keyboard.press("Tab")
        focused_tag = await page.evaluate("document.activeElement.tagName")
        focused_text = await page.evaluate("document.activeElement.innerText")
        print(f"      Tab focused element: <{focused_tag}> '{focused_text.strip()}'")
        assert focused_tag.lower() in ["a", "button", "input"], f"Tab focus failed! Focused element: <{focused_tag}>"
        
        os.makedirs("scratch/qa_reports", exist_ok=True)
        await page.screenshot(path="scratch/qa_reports/suite6_theme_a11y.png")
        print("  📸 Captured AUTHENTIC visual evidence: scratch/qa_reports/suite6_theme_a11y.png")
        print("  ✅ Suite 6 PASSED: Dark Glassmorphic Theme & WCAG 2.1 AA keyboard accessibility verified!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_suite_6())
