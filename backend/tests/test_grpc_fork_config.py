import os
import pytest
from unittest.mock import patch

def test_grpc_fork_support_env():
    """Assert that GRPC_ENABLE_FORK_SUPPORT environment variable is set to '1' or 'true'."""
    import app.main
    assert os.environ.get("GRPC_ENABLE_FORK_SUPPORT") in ("1", "true")

def test_cloud_tasks_lazy_initialization():
    """Assert that CloudTasksService does not initialize CloudTasksClient during construction."""
    # Temporarily remove existing env values if they exist, or mock tasks_v2.CloudTasksClient
    with patch("google.cloud.tasks_v2.CloudTasksClient") as mock_client:
        from app.services.cloud_tasks import CloudTasksService
        
        # Instantiate service
        service = CloudTasksService()
        
        # The constructor should NOT have called CloudTasksClient()
        mock_client.assert_not_called()
        assert not hasattr(service, "_client") or service._client is None or service.client is None
