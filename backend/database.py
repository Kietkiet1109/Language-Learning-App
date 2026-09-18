"""Configure asynchronous SQLAlchemy access to PostgreSQL."""

from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from backend.config import settings


engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
)
session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_database_session() -> AsyncIterator[AsyncSession]:
    """Yield one database session for the lifetime of a request."""

    async with session_factory() as session:
        yield session


async def dispose_database_engine() -> None:
    """Close all database connections owned by the application."""

    await engine.dispose()
