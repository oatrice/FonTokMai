"""
Router: budget_webhook.py
Issue:  #72 — Budget-based Auto-shutdown Mechanism for Cloud Run

รับ Pub/Sub push notification จาก GCP Budget Alert
เมื่อค่าใช้จ่ายถึง 100% ของ budget → scale Cloud Run max-instances = 0
และส่งแจ้งเตือนผ่าน Telegram
"""

import base64
import json
import logging
import os
import subprocess
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/internal",
    tags=["internal"],
)

# ─────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────

class PubSubMessage(BaseModel):
    data: str  # base64-encoded JSON
    messageId: str | None = None
    publishTime: str | None = None
    attributes: dict[str, str] | None = None


class PubSubPushPayload(BaseModel):
    message: PubSubMessage
    subscription: str | None = None


# ─────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────

GCP_PROJECT_ID = os.getenv("GCP_PROJECT", os.getenv("GOOGLE_CLOUD_PROJECT", "fonmayang"))
GCP_REGION = os.getenv("GCP_LOCATION", "asia-southeast1")
CLOUD_RUN_SERVICE = os.getenv("CLOUD_RUN_SERVICE_NAME", "fontokmai-api")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DEVELOPER_CHAT_IDS = os.getenv("DEVELOPER_CHAT_IDS", "")


# ─────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────

def _parse_pubsub_data(encoded_data: str) -> dict[str, Any]:
    """Decode base64 Pub/Sub message data → dict"""
    try:
        decoded = base64.b64decode(encoded_data).decode("utf-8")
        return json.loads(decoded)
    except Exception as e:
        logger.error(f"[BudgetAlert] Failed to decode Pub/Sub message: {e}")
        raise ValueError(f"Invalid Pub/Sub message data: {e}") from e


def _is_budget_exceeded(budget_data: dict[str, Any]) -> bool:
    """
    ตรวจว่า budget ถูกใช้จนถึง 100% แล้วหรือยัง

    GCP Budget Alert schema:
    {
      "budgetDisplayName": "...",
      "alertThresholdExceeded": 1.0,  ← triggered threshold (0.8 or 1.0)
      "costAmount": 10.5,
      "costIntervalStart": "...",
      "budgetAmount": 10.0,
      "budgetAmountType": "SPECIFIED_AMOUNT",
      "currencyCode": "USD"
    }
    """
    alert_threshold = budget_data.get("alertThresholdExceeded", 0.0)
    cost_amount = budget_data.get("costAmount", 0.0)
    budget_amount = budget_data.get("budgetAmount", 1.0)

    # ถือว่า budget exceeded ถ้า threshold >= 1.0 (100%)
    # หรือ cost/budget ratio >= 1.0
    ratio = cost_amount / budget_amount if budget_amount > 0 else 0.0

    logger.info(
        f"[BudgetAlert] threshold={alert_threshold:.2f}, "
        f"cost=${cost_amount:.2f}, budget=${budget_amount:.2f}, ratio={ratio:.2f}"
    )

    return alert_threshold >= 1.0 or ratio >= 1.0


def _revoke_public_access() -> str:
    """
    สั่งลบสิทธิ์ allUsers บน Cloud Run service (ทำให้เข้าถึงไม่ได้ = ปิด) ผ่าน REST API
    Returns: "REVOKED", "ALREADY_PRIVATE", or "ERROR"
    """
    try:
        import google.auth
        from google.auth.transport.requests import Request as GoogleAuthRequest
        import httpx

        # Get default credentials (works seamlessly on Cloud Run)
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        credentials.refresh(GoogleAuthRequest())
        token = credentials.token

        resource = f"projects/{GCP_PROJECT_ID}/locations/{GCP_REGION}/services/{CLOUD_RUN_SERVICE}"
        url_get = f"https://run.googleapis.com/v1/{resource}:getIamPolicy"
        url_set = f"https://run.googleapis.com/v1/{resource}:setIamPolicy"

        with httpx.Client(timeout=10) as client:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # 1. Get current policy
            resp_get = client.get(url_get, headers=headers)
            if resp_get.status_code != 200:
                logger.error(f"[BudgetAlert] ❌ Failed to get IAM policy: {resp_get.text}")
                return "ERROR"
                
            policy = resp_get.json()
            
            # 2. Modify policy: remove allUsers from roles/run.invoker
            modified = False
            for binding in policy.get("bindings", []):
                if binding.get("role") == "roles/run.invoker":
                    if "allUsers" in binding.get("members", []):
                        binding["members"].remove("allUsers")
                        modified = True
            
            if not modified:
                logger.info(f"[BudgetAlert] ✅ Cloud Run '{CLOUD_RUN_SERVICE}' is already private.")
                return "ALREADY_PRIVATE"
                
            # 3. Set updated policy
            resp_set = client.post(url_set, headers=headers, json={"policy": policy})
            if resp_set.status_code == 200:
                logger.info(f"[BudgetAlert] ✅ Cloud Run '{CLOUD_RUN_SERVICE}' public access revoked (Suspended).")
                return "REVOKED"
            else:
                logger.error(f"[BudgetAlert] ❌ Failed to set IAM policy: {resp_set.text}")
                return "ERROR"

    except Exception as e:
        logger.error(f"[BudgetAlert] ❌ Exception during IAM modification: {e}")
        return "ERROR"


async def _send_telegram_alert(message: str) -> None:
    """ส่งข้อความแจ้งเตือนผ่าน Telegram"""
    if not TELEGRAM_BOT_TOKEN or not DEVELOPER_CHAT_IDS:
        logger.warning("[BudgetAlert] Telegram not configured, skipping notification.")
        return

    import httpx

    chat_ids = [cid.strip() for cid in DEVELOPER_CHAT_IDS.split(",") if cid.strip()]
    async with httpx.AsyncClient() as client:
        for chat_id in chat_ids:
            try:
                await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": message,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                    timeout=10,
                )
            except Exception as e:
                logger.error(f"[BudgetAlert] Failed to send Telegram alert to {chat_id}: {e}")


# ─────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────

@router.post(
    "/budget-alert",
    status_code=status.HTTP_200_OK,
    summary="GCP Budget Alert Pub/Sub Handler",
    description=(
        "รับ Pub/Sub push message จาก GCP Budget Alert. "
        "ถ้าค่าใช้จ่ายถึง 100% ของ budget จะสั่ง scale Cloud Run max-instances=0 "
        "และส่งแจ้งเตือนผ่าน Telegram"
    ),
)
async def handle_budget_alert(payload: PubSubPushPayload, request: Request):
    """
    Pub/Sub push subscription endpoint สำหรับ GCP Budget Alert

    GCP จะ POST มาในรูปแบบ:
    {
      "message": {
        "data": "<base64-encoded-json>",
        "messageId": "...",
        "publishTime": "..."
      },
      "subscription": "projects/.../subscriptions/billing-alerts-sub"
    }
    """
    logger.info(f"[BudgetAlert] Received Pub/Sub message: {payload.message.messageId}")

    # Decode และ parse ข้อมูล budget
    try:
        budget_data = _parse_pubsub_data(payload.message.data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    budget_name = budget_data.get("budgetDisplayName", "unknown")
    cost_amount = budget_data.get("costAmount", 0.0)
    budget_amount = budget_data.get("budgetAmount", 0.0)
    currency = budget_data.get("currencyCode", "USD")
    alert_threshold = budget_data.get("alertThresholdExceeded", 0.0)

    logger.info(
        f"[BudgetAlert] Budget '{budget_name}': "
        f"cost={cost_amount} {currency}, budget={budget_amount} {currency}, "
        f"threshold={alert_threshold:.0%}"
    )

    # ─── Warning Alert (80%) ───
    if 0.79 < alert_threshold < 1.0:
        warning_msg = (
            f"⚠️ <b>Budget Warning — FonMaYang</b>\n\n"
            f"📊 ค่าใช้จ่ายถึง <b>{alert_threshold:.0%}</b> ของ budget แล้ว\n"
            f"💰 ค่าใช้จ่ายปัจจุบัน: <code>{cost_amount:.2f} {currency}</code>\n"
            f"🎯 Budget limit: <code>{budget_amount:.2f} {currency}</code>\n"
            f"🔔 ถ้าถึง 100% ระบบจะ scale down Cloud Run อัตโนมัติ"
        )
        await _send_telegram_alert(warning_msg)
        logger.info("[BudgetAlert] ⚠️ 80% warning alert sent.")
        return {"status": "warning_sent", "threshold": alert_threshold}

    # ─── Shutdown Trigger (100%) ───
    if _is_budget_exceeded(budget_data):
        logger.warning("[BudgetAlert] 🚨 Budget 100% exceeded! Initiating Cloud Run shutdown...")

        scale_status = _revoke_public_access()

        if scale_status == "REVOKED":
            shutdown_msg = (
                f"🚨 <b>Budget Exceeded — Emergency Shutdown</b>\n\n"
                f"⚡ สิทธิ์การเข้าถึงแบบ Public (allUsers) ของ <code>{CLOUD_RUN_SERVICE}</code> ถูกระงับแล้ว (ไม่มีการรับ traffic ใหม่)\n\n"
                f"💳 ค่าใช้จ่ายปัจจุบัน: <code>{cost_amount:.2f} {currency}</code>\n"
                f"🎯 Budget limit: <code>{budget_amount:.2f} {currency}</code>\n\n"
                f"ℹ️ เพื่อ restore service ให้กลับมาออนไลน์:\n"
                f"<code>gcloud run services add-iam-policy-binding {CLOUD_RUN_SERVICE} --region={GCP_REGION} --member=\"allUsers\" --role=\"roles/run.invoker\"</code>"
            )
            await _send_telegram_alert(shutdown_msg)
            return {"status": "shutdown_success", "cost": cost_amount, "budget": budget_amount}
            
        elif scale_status == "ALREADY_PRIVATE":
            # Deduplicate alert: if it's already private, we don't spam Telegram again
            logger.info("[BudgetAlert] Muting duplicate Telegram alert because service is already private.")
            return {"status": "already_private", "cost": cost_amount, "budget": budget_amount}

        else:
            shutdown_msg = (
                f"🔴 <b>Budget Exceeded — Shutdown FAILED</b>\n\n"
                f"❌ ไม่สามารถระงับการเข้าถึง Cloud Run ได้ กรุณาตรวจสอบด่วน!\n\n"
                f"💳 ค่าใช้จ่าย: <code>{cost_amount:.2f} {currency}</code> / <code>{budget_amount:.2f} {currency}</code>\n"
                f"🛠️ กรุณาระงับ manually:\n"
                f"<code>gcloud run services remove-iam-policy-binding {CLOUD_RUN_SERVICE} --region={GCP_REGION} --member=\"allUsers\" --role=\"roles/run.invoker\"</code>"
            )
            await _send_telegram_alert(shutdown_msg)
            return {"status": "shutdown_failed", "cost": cost_amount, "budget": budget_amount}

    # ─── Normal notification (ไม่ถึง threshold สำคัญ) ───
    logger.info(f"[BudgetAlert] Notification received but no action needed (threshold={alert_threshold:.0%}).")
    return {"status": "acknowledged", "threshold": alert_threshold}
