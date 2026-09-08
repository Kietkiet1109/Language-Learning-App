"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncIterator
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import dispose_database_engine, get_database_session


@asynccontextmanager
async def application_lifespan(_application: FastAPI) -> AsyncIterator[None]:
    """Manage resources owned by the FastAPI application."""

    yield
    await dispose_database_engine()


app = FastAPI(
    title="Prononcia API",
    version="0.1.0",
    lifespan=application_lifespan,
)


@app.get("/health")
async def health_check(
    session: AsyncSession = Depends(get_database_session),
) -> dict[str, str]:
    """Report whether the API can reach PostgreSQL."""

    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return {"status": "unhealthy", "database": "unavailable"}

    return {"status": "healthy", "database": "available"}
