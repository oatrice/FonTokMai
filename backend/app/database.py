import os
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./fonmayang.db")

# Automatically switch to asyncpg for Neon Postgres
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Clean unsupported query parameters for asyncpg (e.g. channel_binding, sslmode from Neon connection strings)
if "postgresql+asyncpg://" in DATABASE_URL:
    parsed = urlparse(DATABASE_URL)
    if parsed.query:
        query_params = parse_qs(parsed.query)
        # asyncpg does not accept channel_binding or sslmode as kwargs
        query_params.pop("channel_binding", None)
        has_sslmode = query_params.pop("sslmode", None)
        
        # Convert sslmode=require to ssl=require for asyncpg
        if has_sslmode and "ssl" not in query_params:
            ssl_val = has_sslmode[0] if isinstance(has_sslmode, list) else has_sslmode
            query_params["ssl"] = ["require" if ssl_val in ("require", "verify-ca", "verify-full") else ssl_val]

        new_query = urlencode(query_params, doseq=True)
        DATABASE_URL = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))

engine = create_async_engine(
    DATABASE_URL, 
    echo=False, 
    pool_pre_ping=True,
    connect_args={
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0
    }
)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
