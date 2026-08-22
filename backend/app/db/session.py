from typing import AsyncGenerator
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.core.logging import logger

def get_normalized_database_urls():
    """
    Normalizes database connection strings for both Async (FastAPI) and Sync (CLI/Ingestion) engines.
    Automatically handles 'postgres://', 'postgresql://', and 'postgresql+asyncpg://' formats seamlessly.
    """
    raw_async = os.getenv("DATABASE_URL", settings.DATABASE_URL)
    raw_sync = os.getenv("SYNC_DATABASE_URL", settings.SYNC_DATABASE_URL or raw_async)

    # Base URL to normalize
    base_url = raw_async or raw_sync

    # Normalize Async URL (MUST use postgresql+asyncpg:// for async engine)
    if base_url.startswith("postgres://"):
        async_url = base_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif base_url.startswith("postgresql://"):
        async_url = base_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        async_url = base_url

    # Normalize Sync URL (MUST use postgresql:// for sync engine)
    if raw_sync.startswith("postgres://"):
        sync_url = raw_sync.replace("postgres://", "postgresql://", 1)
    elif raw_sync.startswith("postgresql+asyncpg://"):
        sync_url = raw_sync.replace("postgresql+asyncpg://", "postgresql://", 1)
    else:
        sync_url = raw_sync or async_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    return async_url, sync_url

active_async_url, active_sync_url = get_normalized_database_urls()

# Supabase / PgBouncer compatibility flags
is_pgbouncer = (
    "pooler.supabase.com" in active_async_url or 
    ":6543" in active_async_url or 
    "supabase" in active_async_url.lower()
)

async_connect_args = {}
if "asyncpg" in active_async_url:
    # Disable prepared statement caching for Supabase PgBouncer transaction pooling
    async_connect_args["statement_cache_size"] = 0
    async_connect_args["prepared_statement_cache_size"] = 0

# Async Engine (for FastAPI request handlers)
async_engine = create_async_engine(
    active_async_url,
    echo=False,
    pool_pre_ping=True,
    poolclass=NullPool if is_pgbouncer else None,
    connect_args=async_connect_args
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Sync Engine (for CLI ingestion and migrations)
sync_engine = create_engine(
    active_sync_url,
    echo=False,
    pool_pre_ping=True,
    poolclass=NullPool if is_pgbouncer else None
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False
)

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for injecting async database sessions in FastAPI routes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

def get_sync_db() -> Session:
    """Helper for standalone scripts and ingestion pipelines."""
    db = SyncSessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        logger.error(f"Sync database session error: {e}")
        raise
