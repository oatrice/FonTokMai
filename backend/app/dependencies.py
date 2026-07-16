import os
import httpx
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from app.repositories.base import LocationRepository
from app.repositories.sqlite import SQLiteLocationRepository
from app.database import AsyncSessionLocal

_http_client: httpx.AsyncClient | None = None

def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client

async def close_http_client() -> None:
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None

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
