import os
import json
import logging
from typing import Dict, Any, Optional
from google.cloud import tasks_v2

logger = logging.getLogger(__name__)

class CloudTasksService:
    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT", "fonmayang")
        self.location = os.getenv("GCP_LOCATION", "asia-southeast1")
        self.queue_name = os.getenv("CLOUD_TASKS_QUEUE", "webhook-worker-queue")
        
        # The absolute URL where the worker endpoints are hosted
        self.base_url = os.getenv("WORKER_BASE_URL")
        
        try:
            self.client = tasks_v2.CloudTasksClient()
            self.parent = self.client.queue_path(self.project_id, self.location, self.queue_name)
        except Exception as e:
            logger.warning(f"Could not initialize Cloud Tasks client: {e}")
            self.client = None

    def enqueue_task(self, endpoint_path: str, payload: Dict[str, Any], in_seconds: int = 0) -> Optional[str]:
        """
        Enqueues an HTTP POST task to the worker router.
        """
        if not self.client or not self.base_url:
            logger.warning(f"Cloud Tasks client or WORKER_BASE_URL not configured. Cannot enqueue to {endpoint_path}.")
            return None

        url = f"{self.base_url.rstrip('/')}/{endpoint_path.lstrip('/')}"
        
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": url,
                "headers": {"Content-type": "application/json"},
                "body": json.dumps(payload).encode(),
            }
        }

        if in_seconds > 0:
            import datetime
            from google.protobuf import timestamp_pb2
            d = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=in_seconds)
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(d)
            task["schedule_time"] = timestamp

        try:
            response = self.client.create_task(request={"parent": self.parent, "task": task})
            logger.info(f"Created task {response.name} for {url}")
            return response.name
        except Exception as e:
            logger.error(f"Failed to create task for {url}: {e}")
            return None
