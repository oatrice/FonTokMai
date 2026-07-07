import os
import uuid
import logging
import urllib.parse
from abc import ABC, abstractmethod
from typing import Optional, Union

# Line imports
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
    ImageMessage,
)

from app.services.telegram import (
    send_telegram_message,
    send_telegram_photo,
    send_telegram_document,
)

logger = logging.getLogger(__name__)

class NotificationService(ABC):
    @abstractmethod
    async def send_text_message(self, recipient_id: str, text: str, reply_markup: Optional[dict] = None) -> bool:
        """Sends a text message to the recipient."""
        pass

    @abstractmethod
    async def send_photo(self, recipient_id: str, photo_data: bytes, filename: str) -> bool:
        """Sends a photo to the recipient."""
        pass

    @abstractmethod
    async def send_document(self, recipient_id: str, document_data: bytes, filename: str) -> bool:
        """Sends a document (like a GIF) to the recipient."""
        pass


class TelegramNotificationService(NotificationService):
    async def send_text_message(self, recipient_id: str, text: str, reply_markup: Optional[dict] = None) -> bool:
        try:
            chat_id = int(recipient_id)
        except ValueError:
            logger.error(f"Invalid Telegram chat_id: {recipient_id}")
            return False
        return await send_telegram_message(chat_id, text, reply_markup=reply_markup)

    async def send_photo(self, recipient_id: str, photo_data: bytes, filename: str) -> bool:
        try:
            chat_id = int(recipient_id)
        except ValueError:
            logger.error(f"Invalid Telegram chat_id: {recipient_id}")
            return False
        return await send_telegram_photo(chat_id, photo_data, filename)

    async def send_document(self, recipient_id: str, document_data: bytes, filename: str) -> bool:
        try:
            chat_id = int(recipient_id)
        except ValueError:
            logger.error(f"Invalid Telegram chat_id: {recipient_id}")
            return False
        return await send_telegram_document(chat_id, document_data, filename)


class LineNotificationService(NotificationService):
    def __init__(self):
        self.access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "mock_token")
        self.channel_secret = os.getenv("LINE_CHANNEL_SECRET", "mock_secret")
        self.config = Configuration(access_token=self.access_token)

    def _upload_media(self, media_bytes: bytes, content_type: str, file_ext: str) -> Optional[str]:
        """Uploads media bytes to GCS (public) or hosts locally as fallback, returning a public URL."""
        # 1. Try GCS first (preferred for production multi-instance load balancing)
        try:
            from google.cloud import storage
            bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "fonmayang.firebasestorage.app")
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            
            filename = f"temp_media/{uuid.uuid4()}{file_ext}"
            blob = bucket.blob(filename)
            blob.upload_from_string(media_bytes, content_type=content_type)
            
            # Make the object public so LINE can access it without tokens
            try:
                blob.make_public()
                url = blob.public_url
                logger.info(f"Successfully uploaded and made public on GCS: {url}")
                return url
            except Exception as e:
                logger.warning(f"Failed to make GCS blob public, trying signed URL: {e}")
                import datetime
                try:
                    url = blob.generate_signed_url(
                        version="v4",
                        expiration=datetime.timedelta(minutes=30),
                        method="GET"
                    )
                    logger.info(f"Generated GCS signed URL: {url}")
                    return url
                except Exception as sign_err:
                    logger.warning(f"Failed to generate signed URL: {sign_err}")
                    # Fall through to local hosting fallback
        except Exception as gcs_err:
            logger.warning(f"GCS upload failed, falling back to local static hosting: {gcs_err}")

        # 2. Fallback: Host locally (uses ngrok in dev, or local filesystem in production)
        try:
            base_url = os.getenv("WORKER_BASE_URL")
            if base_url:
                static_dir = os.path.join(os.getcwd(), "static", "temp_media")
                os.makedirs(static_dir, exist_ok=True)
                
                filename = f"{uuid.uuid4()}{file_ext}"
                file_path = os.path.join(static_dir, filename)
                with open(file_path, "wb") as f:
                    f.write(media_bytes)
                
                url = f"{base_url.rstrip('/')}/static/temp_media/{filename}"
                logger.info(f"Hosted Line media locally (fallback): {url}")
                return url
        except Exception as local_err:
            logger.error(f"Failed to host Line temp media locally: {local_err}")
            
        return None

    async def send_text_message(self, recipient_id: str, text: str, reply_markup: Optional[dict] = None) -> bool:
        # Line does not use standard telegram reply_markups. We send text messages directly.
        try:
            import asyncio
            def _send():
                if recipient_id.startswith("U1234567890") or self.access_token == "mock_token":
                    logger.info(f"[MOCK LINE PUSH TEXT] Recipient: {recipient_id}\nContent:\n{text}")
                    return True
                with ApiClient(self.config) as api_client:
                    line_bot_api = MessagingApi(api_client)
                    push_message_request = PushMessageRequest(
                        to=recipient_id,
                        messages=[TextMessage(text=text)]
                    )
                    line_bot_api.push_message(push_message_request)
                return True

            return await asyncio.to_thread(_send)
        except Exception as e:
            logger.error(f"Failed to send Line message to {recipient_id}: {e}")
            return False

    async def send_photo(self, recipient_id: str, photo_data: bytes, filename: str) -> bool:
        try:
            import asyncio
            if recipient_id.startswith("U1234567890") or self.access_token == "mock_token":
                logger.info(f"[MOCK LINE PUSH PHOTO] Recipient: {recipient_id}, File: {filename}")
                return True
            url = await asyncio.to_thread(self._upload_media, photo_data, "image/png", ".png")
            if not url:
                logger.error(f"Could not get public URL for photo {filename}")
                return False

            def _send():
                with ApiClient(self.config) as api_client:
                    line_bot_api = MessagingApi(api_client)
                    push_message_request = PushMessageRequest(
                        to=recipient_id,
                        messages=[ImageMessage(original_content_url=url, preview_image_url=url)]
                    )
                    line_bot_api.push_message(push_message_request)
                return True

            return await asyncio.to_thread(_send)
        except Exception as e:
            logger.error(f"Failed to send Line photo to {recipient_id}: {e}")
            return False

    async def send_document(self, recipient_id: str, document_data: bytes, filename: str) -> bool:
        # Since Line doesn't have an exact equivalent of document, we upload and send as ImageMessage
        try:
            import asyncio
            if recipient_id.startswith("U1234567890") or self.access_token == "mock_token":
                logger.info(f"[MOCK LINE PUSH DOC] Recipient: {recipient_id}, File: {filename}")
                return True
            ext = ".gif" if filename.lower().endswith(".gif") else ".png"
            mime = "image/gif" if ext == ".gif" else "image/png"
            url = await asyncio.to_thread(self._upload_media, document_data, mime, ext)
            if not url:
                logger.error(f"Could not get public URL for document {filename}")
                return False

            def _send():
                with ApiClient(self.config) as api_client:
                    line_bot_api = MessagingApi(api_client)
                    push_message_request = PushMessageRequest(
                        to=recipient_id,
                        messages=[ImageMessage(original_content_url=url, preview_image_url=url)]
                    )
                    line_bot_api.push_message(push_message_request)
                return True

            return await asyncio.to_thread(_send)
        except Exception as e:
            logger.error(f"Failed to send Line document to {recipient_id}: {e}")
            return False


# Singleton registry for services
_SERVICES = {
    "telegram": TelegramNotificationService(),
    "line": LineNotificationService()
}

def get_notification_service(platform: str) -> NotificationService:
    return _SERVICES.get(platform.lower(), _SERVICES["telegram"])
