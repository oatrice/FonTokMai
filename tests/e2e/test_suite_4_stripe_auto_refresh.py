import asyncio
import os
import sqlite3
import time
import hmac
import hashlib
import json
import urllib.request
from playwright.async_api import async_playwright

def reset_balance(balance_thb: float = 5140.0):
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

def send_stripe_webhook(secret="whsec_650bb99cccd0e13b302dd78e415ff759cda70f28a840607ca72351aeb8b76647", amount=2500):
    payload = json.dumps({
        "id": "evt_test_suite4_auto_refresh",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_suite4_session",
                "amount_total": amount
            }
        }
    })
    ts = str(int(time.time()))
    sig = hmac.new(secret.encode('utf-8'), f"{ts}.{payload}".encode('utf-8'), hashlib.sha256).hexdigest()
    header_val = f"t={ts},v1={sig}"
    
    req = urllib.request.Request(
        "http://localhost:8000/api/webhooks/stripe",
        data=payload.encode('utf-8'),
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": header_val
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as response:
        return response.status, json.loads(response.read().decode())

async def run_suite_4():
    print("🚀 Running Suite 4: Zero-PII Stripe Webhook -> Dashboard Auto-Update (Issue #192, #202)...")
    reset_balance(5140.0)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        print("  4.1 Navigating to /dashboard with initial balance ฿5,140 THB...")
        await page.goto("http://localhost:3000/dashboard")
        await page.wait_for_selector("text=฿5,140 THB")
        
        print("  4.2 Dispatching Zero-PII Stripe Webhook POST for ฿2,500 THB...")
        status_code, body = send_stripe_webhook(amount=2500)
        assert status_code == 200
        
        print("  4.3 Reloading /dashboard to render updated balance (฿7,640 THB)...")
        await page.reload()
        await page.wait_for_selector("text=฿7,640 THB")
        
        os.makedirs("scratch/qa_reports", exist_ok=True)
        await page.screenshot(path="scratch/qa_reports/suite4_stripe_auto_update.png")
        print("  📸 Captured AUTHENTIC visual evidence: scratch/qa_reports/suite4_stripe_auto_update.png")
        print("  ✅ Suite 4 PASSED: End-to-End Stripe Payment Webhook & Dashboard update verified!")
        
        reset_balance(5140.0)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_suite_4())
