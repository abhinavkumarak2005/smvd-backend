import asyncpg
import logging
from typing import AsyncGenerator

from app.config import get_settings

logger = logging.getLogger(__name__)

# Global pool — initialized at startup, closed at shutdown
_pool: asyncpg.Pool | None = None


async def init_db() -> None:
    """Create the asyncpg connection pool. Called at FastAPI startup."""
    global _pool
    settings = get_settings()
    try:
        _pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=5,
            max_size=20,
            command_timeout=60,
            statement_cache_size=0,
        )
        # Quick health check on startup
        async with _pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        logger.info("Database pool initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
        raise


async def close_db() -> None:
    """Close the asyncpg connection pool. Called at FastAPI shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        logger.info("Database pool closed.")


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    FastAPI dependency — yields a single connection from the pool.
    Use with: conn: asyncpg.Connection = Depends(get_db)
    """
    if _pool is None:
        raise RuntimeError("Database pool is not initialized.")
    async with _pool.acquire() as connection:
        yield connection


async def check_db_health() -> bool:
    """Returns True if database is reachable, False otherwise."""
    if _pool is None:
        return False
    try:
        async with _pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception:
        return False

def get_db_pool() -> asyncpg.Pool | None:
    """Returns the raw asyncpg connection pool for background jobs."""
    return _pool
