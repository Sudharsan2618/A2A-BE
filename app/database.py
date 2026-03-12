"""
LuxeLife API — Async SQLAlchemy database engine and session management.

Design decisions:
- Uses asyncpg driver for true async I/O with PostgreSQL.
- Connection pool is configured via settings (pool_size, max_overflow, recycle).
- Sessions use expire_on_commit=False so objects remain usable after commit.
- The get_db dependency manages the session lifecycle per-request:
  commit on success, rollback on exception, close always.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# ── Engine ──
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=settings.DB_ECHO,
)

# ── Session Factory ──
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session.

    - Commits automatically if the request handler succeeds.
    - Rolls back on any exception to prevent partial writes.
    - Always closes the session to return the connection to the pool.
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
