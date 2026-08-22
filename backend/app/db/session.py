from typing import AsyncGenerator
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.core.logging import logger

def get_database_urls():
    """
    Determines active async and sync database connection URLs.
    Supports PostgreSQL (local PGAdmin / Supabase) with automatic SQLite local development fallback.
    """
    db_url = settings.DATABASE_URL
    sync_url = settings.SYNC_DATABASE_URL
    
    # Check if postgres credentials might need fallback during initial setup
    if "postgresql" in db_url:
        try:
            import psycopg2
            # Quick check if connection works with current settings
            # If not configured yet, use local SQLite so the app runs out-of-the-box
            import urllib.parse
            parsed = urllib.parse.urlparse(sync_url)
            conn = psycopg2.connect(
                dbname=parsed.path.lstrip('/') or 'postgres',
                user=parsed.username or 'postgres',
                password=parsed.password or 'postgres',
                host=parsed.hostname or 'localhost',
                port=parsed.port or 5432,
                connect_timeout=2
            )
            conn.close()
            logger.info("Connected to PostgreSQL database successfully.")
            return db_url, sync_url
        except Exception as e:
            logger.info(f"PostgreSQL connection requires PGAdmin credentials ({e}). Using local sqlite database for seamless operation.")
            sqlite_async = "sqlite+aiosqlite:///./interviewquest.db"
            sqlite_sync = "sqlite:///./interviewquest.db"
            return sqlite_async, sqlite_sync
            
    return db_url, sync_url

active_async_url, active_sync_url = get_database_urls()

# Async Engine (for FastAPI request handlers)
async_engine = create_async_engine(
    active_async_url,
    echo=False,
    pool_pre_ping=True
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
    pool_pre_ping=True
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
