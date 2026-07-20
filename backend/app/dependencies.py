import os
import httpx
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from app.repositories.base import LocationRepository
from app.repositories.sqlite import SQLiteLocationRepository
from app.database import AsyncSessionLocal

import asyncio

_http_client: httpx.AsyncClient | None = None
_http_client_loop: asyncio.AbstractEventLoop | None = None

def get_http_client() -> httpx.AsyncClient:
    global _http_client, _http_client_loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _http_client is None or _http_client.is_closed or _http_client_loop != current_loop:
        _http_client = httpx.AsyncClient(timeout=30.0)
        _http_client_loop = current_loop
    return _http_client

async def close_http_client() -> None:
    global _http_client, _http_client_loop
    if _http_client is not None and not _http_client.is_closed:
        try:
            current_loop = asyncio.get_running_loop()
            if _http_client_loop == current_loop:
                await _http_client.aclose()
        except RuntimeError:
            pass
    _http_client = None
    _http_client_loop = None

def get_firestore_repo():
    from app.repositories.firestore import FirestoreLocationRepository
    return FirestoreLocationRepository()

@asynccontextmanager
async def get_repo_context() -> AsyncGenerator[LocationRepository, None]:
    backend = os.getenv("STORAGE_BACKEND", "sqlite").lower()
    
    if backend == "firestore":
        yield get_firestore_repo()
    else:
        async with AsyncSessionLocal() as session:
            yield SQLiteLocationRepository(session)

# For FastAPI Depends()
async def get_location_repo() -> AsyncGenerator[LocationRepository, None]:
    async with get_repo_context() as repo:
        yield repo
