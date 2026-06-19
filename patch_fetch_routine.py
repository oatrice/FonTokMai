import re

with open("backend/app/scheduler_tasks.py", "r") as f:
    content = f.read()

# We need to replace `async def _process_station(station: str) -> dict:` block
# up to `station_results = await asyncio.gather(`

start_pattern = "    async def _process_station(station: str) -> dict:"
end_pattern = "    # Run all stations in PARALLEL"

start_idx = content.find(start_pattern)
end_idx = content.find(end_pattern)

if start_idx != -1 and end_idx != -1:
    new_func = """    async def _process_station(station: str) -> dict:
        result = {"station": station, "updated": False, "error": None}
        try:
            processor = TMDRadarProcessor(station_code=station)

            # 1. Fetch static image bytes
            static_bytes = await processor.fetch_latest_image_bytes(use_cache=False)
            if not static_bytes:
                logger.warning(f"[{station}] Could not fetch static image.")
                return result

            # 2. Extract timestamp via OCR
            from app.services.ocr_service import OCRService
            import numpy as np
            import cv2
            
            np_arr = np.frombuffer(static_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            # Since OpenCV reads in BGR, we convert to RGB for consistency with original PIL logic
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            ocr_svc = OCRService()
            now_ts = int(datetime.now(timezone.utc).timestamp())
            ts = await ocr_svc.get_frame_timestamp(frame, fallback_ts=now_ts)

            # 3. Check cache
            async with get_repo_context() as repo:
                cache = await repo.get_latest_radar_cache(station)
                
                # If we already have this timestamp, do nothing
                if cache and ts and ts <= cache.get("timestamp", 0):
                    logger.debug(f"[{station}] Image unchanged (ts {ts}). Skipping.")
                    return result
                
                # It's a new image!
                new_url_t = await processor.save_polled_frame(static_bytes)
                url_t_minus_1 = cache.get("url_t") if cache else None
                
                await repo.set_latest_radar_cache(
                    station_code=station,
                    url_t=new_url_t,
                    url_t_minus_1=url_t_minus_1,
                    timestamp=ts
                )
                logger.info(f"Updated Firestore radar cache for {station} with ts {ts}")

            # Cleanup old frames
            deleted = await processor.cleanup_old_frames(max_age_hours=3)
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old frames for {station}")

            # Clean up memory explicitly
            del frame
            del np_arr
            import gc
            gc.collect()

            result["updated"] = True
        except Exception as e:
            logger.error(f"Failed to cache TMD radar for {station}: {e}")
            result["error"] = str(e)
        return result

"""
    new_content = content[:start_idx] + new_func + content[end_idx:]
    with open("backend/app/scheduler_tasks.py", "w") as out_f:
        out_f.write(new_content)
    print("Patched _process_station successfully!")
else:
    print("Could not find patterns!")
