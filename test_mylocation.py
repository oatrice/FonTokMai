import asyncio
from app.routers.webhook import handle_mylocation_command, handle_callback_query
from app.repositories.firestore import FirestoreLocationRepository
from app.dependencies import get_repo_context
from unittest.mock import patch, MagicMock, AsyncMock

async def main():
    chat_id = 123456789
    repo = FirestoreLocationRepository()
    
    # 1. Add an old location (no name)
    doc_ref = repo.collection.document(str(chat_id))
    await doc_ref.set({"chat_id": chat_id, "latitude": 13.0, "longitude": 100.0, "retention_type": "FOREVER"})
    
    # 2. Add a new location (name = home)
    await repo.save_location(chat_id, 14.0, 101.0, "FOREVER", "home")
    
    print("Testing /mylocation")
    with patch("app.routers.webhook.send_telegram_message", new_callable=AsyncMock) as mock_send:
        await handle_mylocation_command(chat_id)
        mock_send.assert_called_once()
        print("Message sent:", mock_send.call_args)
        
    print("Testing callback loc_del_home")
    cb = {
        "id": "query1",
        "from": {"id": chat_id},
        "data": "loc_del_home",
        "message": {"message_id": 999}
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        await handle_callback_query(cb)
        print("Post called:", mock_post.call_args_list)

asyncio.run(main())
