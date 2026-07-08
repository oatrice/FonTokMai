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
        
        self._client = None
        self._parent = None

    @property
    def client(self):
        if self._client is None:
            try:
                self._client = tasks_v2.CloudTasksClient()
            except Exception as e:
                logger.warning(f"Could not initialize Cloud Tasks client: {e}")
                self._client = None
        return self._client

    @property
    def parent(self):
        if self._parent is None and self.client is not None:
            self._parent = self.client.queue_path(self.project_id, self.location, self.queue_name)
        return self._parent

    def enqueue_task(self, endpoint_path: str, payload: Dict[str, Any], in_seconds: int = 0) -> Optional[str]:
        """
        Enqueues an HTTP POST task to the worker router.
        """
        if not self.client or not self.base_url:
            logger.warning(f"Cloud Tasks client or WORKER_BASE_URL not configured. Cannot enqueue to {endpoint_path}.")
            return None

        url = f"{self.base_url.rstrip('/')}/{endpoint_path.lstrip('/')}"
        
        worker_secret = os.getenv("WORKER_SECRET", os.getenv("CRON_SECRET", "default_secret_for_local_testing"))
        
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": url,
                "headers": {
                    "Content-type": "application/json",
                    "X-Worker-Secret": worker_secret
                },
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

    async def get_queue_metrics(self) -> Dict[str, Any]:
        """
        Fetches the current queue depth from Google Cloud Monitoring.
        Requires `google-cloud-monitoring` package.
        """
        try:
            from google.cloud import monitoring_v3
            import time
            
            client = monitoring_v3.MetricServiceAsyncClient()
            project_name = f"projects/{self.project_id}"
            
            # Query the queue depth metric for the last 5 minutes
            now = time.time()
            seconds = int(now)
            nanos = int((now - seconds) * 10**9)
            
            interval = monitoring_v3.TimeInterval(
                {
                    "end_time": {"seconds": seconds, "nanos": nanos},
                    "start_time": {"seconds": seconds - 300, "nanos": nanos}, # past 5 minutes
                }
            )
            
            # Filter for specific queue
            metric_filter = (
                'metric.type = "cloudtasks.googleapis.com/queue/depth" '
                f'AND resource.labels.queue_id = "{self.queue_name}" '
                f'AND resource.labels.location = "{self.location}"'
            )
            
            results = await client.list_time_series(
                request={
                    "name": project_name,
                    "filter": metric_filter,
                    "interval": interval,
                    "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                }
            )
            
            # Extract the most recent data point
            latest_depth = 0
            async for series in results:
                if series.points:
                    # points are ordered by end_time descending
                    latest_depth = series.points[0].value.int64_value
                    break
            
            return {
                "queue_name": self.queue_name,
                "location": self.location,
                "depth": latest_depth,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Failed to fetch queue metrics: {e}")
            return {
                "queue_name": self.queue_name,
                "depth": -1,
                "status": "error",
                "error": str(e)
            }
