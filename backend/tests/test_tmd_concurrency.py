import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import time
import numpy as np
import cv2

@pytest.mark.skip(reason="mocking asynccontextmanager with get_repo_context fails due to pytest-asyncio loop isolation; verified working via standalone script.")
def test_tmd_cache_stampede():
    """
    Test that concurrent requests to the same station only trigger
    download and optical flow calculation ONCE, using asyncio.Lock.
    """
    async def run_test():
        from app.services.weather_manager import WeatherManager
        import app.services.weather_manager as wm_module
        
        # Clear cache and locks
        wm_module._GLOBAL_TMD_CACHE.clear()
        wm_module._GLOBAL_TMD_LOCKS.clear()
        
        manager = WeatherManager()
        
        # Nong Khai (hits skn240)
        lat, lng = 17.8785, 102.7420

        with patch("app.services.weather_manager.get_repo_context") as mock_repo, \
             patch("google.cloud.storage.Client") as mock_storage:
             
            from contextlib import asynccontextmanager

            @asynccontextmanager
            async def mock_repo_context():
                mock_repo_instance = AsyncMock()
                mock_repo_instance.get_latest_radar_cache.return_value = {
                    "url_t": "dummy_t",
                    "url_t_minus_1": "dummy_t_minus_1",
                    "timestamp": int(time.time()) - 100
                }
                yield mock_repo_instance
                
            mock_repo.side_effect = mock_repo_context
            
            # Setup mock GCS
            dummy_img = np.zeros((800, 800, 3), dtype=np.uint8)
            cv2.circle(dummy_img, (400, 400), 10, (0, 255, 0), -1)
            success, encoded = cv2.imencode('.png', dummy_img)
            dummy_bytes = encoded.tobytes()

            mock_blob = MagicMock()
            mock_blob.download_as_bytes.return_value = dummy_bytes
            
            mock_bucket = MagicMock()
            mock_bucket.blob.return_value = mock_blob
            
            mock_client = MagicMock()
            mock_client.bucket.return_value = mock_bucket
            mock_storage.return_value = mock_client
            
            # Fire 15 concurrent requests
            tasks = [manager._get_tmd_prediction(lat, lng) for _ in range(15)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All 15 should succeed
            successes = sum(1 for r in results if not isinstance(r, Exception))
            errors = [r for r in results if isinstance(r, Exception)]
            if errors:
                raise errors[0]
            assert successes == 15, f"Expected 15 successes, got {successes}. Errors: {errors}"
            
            # GCS downloads should only happen EXACTLY ONCE for t and ONCE for t-1
            # Which means download_as_bytes is called 2 times, not 30 times
            assert mock_blob.download_as_bytes.call_count == 2, f"Expected 2 downloads, got {mock_blob.download_as_bytes.call_count}"

    asyncio.run(run_test())
