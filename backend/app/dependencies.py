import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from app.repositories.base import LocationRepository
from app.repositories.sqlite import SQLiteLocationRepository
from app.database import AsyncSessionLocal

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
