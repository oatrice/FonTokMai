import base64
import json
import os
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
DEVELOPER_CHAT_IDS = os.environ.get('DEVELOPER_CHAT_IDS', '')

def telegram_pubsub_handler(event, context):
    """
    Background Cloud Function to be triggered by Pub/Sub.
    Expects GCP Monitoring Incident payload in the Pub/Sub message.
    """
    if not TELEGRAM_BOT_TOKEN or not DEVELOPER_CHAT_IDS:
        logger.error("Missing TELEGRAM_BOT_TOKEN or DEVELOPER_CHAT_IDS environment variables.")
        return

    try:
        # The payload is base64 encoded inside the 'data' field of the event
        pubsub_message = base64.b64decode(event['data']).decode('utf-8')
        logger.info(f"Received raw Pub/Sub message: {pubsub_message}")
        
        payload = json.loads(pubsub_message)
        
        # GCP Monitoring Incident payload structure
        incident = payload.get('incident', {})
        if not incident:
            logger.warning("No 'incident' field found in payload. Ignoring.")
            return

        state = incident.get('state', 'unknown')
        summary = incident.get('summary', 'No summary provided')
        url = incident.get('url', '')
        
        # Format the Telegram message
        if state == 'open':
            emoji = "🚨"
            status_text = "<b>[ALERT]</b>"
        elif state == 'closed':
            emoji = "✅"
            status_text = "<b>[RESOLVED]</b>"
        else:
            emoji = "ℹ️"
            status_text = f"<b>[{state.upper()}]</b>"

        message = (
            f"{emoji} {status_text} <b>GCP Monitoring</b>\n\n"
            f"<b>Details:</b> {summary}\n\n"
            f"<a href='{url}'>🔍 View Incident in GCP Console</a>"
        )
        
        # Send to Telegram
        chat_ids = [cid.strip() for cid in DEVELOPER_CHAT_IDS.split(',') if cid.strip()]
        for chat_id in chat_ids:
            send_telegram_message(chat_id, message)
            
    except Exception as e:
        logger.error(f"Error processing pubsub message: {e}")

def send_telegram_message(chat_id, text):
    """Sends a message to the specified Telegram chat ID."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully sent alert to {chat_id}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")
        if e.response is not None:
            logger.error(f"Response: {e.response.text}")
