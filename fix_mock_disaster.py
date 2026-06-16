with open('backend/app/scheduler_tasks.py', 'a') as f:
    f.write("""

async def trigger_mock_disaster(payload_dict: dict):
    \"\"\"Process a mock disaster payload.\"\"\"
    import time
    from app.dependencies import get_repo_context
    from app.services.disaster_manager import process_disaster_event
    
    timestamp = int(time.time())
    event_id = f"postman_mock_{timestamp}"
    
    event_data = {
        "id": event_id,
        "lat": payload_dict.get("lat"),
        "lng": payload_dict.get("lng"),
    }
    
    disaster_type = payload_dict.get("type", "earthquake")
    
    if disaster_type == "earthquake":
        event_data["mag"] = payload_dict.get("mag")
        event_data["place"] = payload_dict.get("name")
    elif disaster_type == "cyclone":
        event_data["name"] = payload_dict.get("name")
        event_data["category"] = "Cat 4"
    elif disaster_type == "fire":
        event_data["name"] = payload_dict.get("name")
        
    async with get_repo_context() as repo:
        await process_disaster_event(repo, disaster_type, event_data)
""")

import re

with open('backend/app/routers/scheduler.py', 'r') as f:
    sched_content = f.read()

sched_content = re.sub(
    r'async def run_mock\(\):.*?background_tasks\.add_task\(run_mock\)',
    'from app.scheduler_tasks import trigger_mock_disaster\n        background_tasks.add_task(trigger_mock_disaster, payload.model_dump())',
    sched_content,
    flags=re.DOTALL
)
with open('backend/app/routers/scheduler.py', 'w') as f:
    f.write(sched_content)

with open('backend/app/routers/worker.py', 'r') as f:
    worker_content = f.read()

worker_content = worker_content.replace(
    'async def worker_trigger_mock_disaster():',
    'async def worker_trigger_mock_disaster(payload: dict):'
)
worker_content = worker_content.replace(
    'await trigger_mock_disaster()',
    'await trigger_mock_disaster(payload)'
)
with open('backend/app/routers/worker.py', 'w') as f:
    f.write(worker_content)
    
print("Mock disaster fixed.")
