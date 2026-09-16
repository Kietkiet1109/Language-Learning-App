"""FastAPI application entry point for Prononcia."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import dispose_database_engine, get_database_session
from video_processing.schemas import (
    ProcessVideoRequest,
    ProcessVideoResponse,
    ResegmentationResponse,
    VideoPartsResponse,
)
from video_processing.service import (
    InvalidVideoUrlError,
    UnsupportedVideoUrlError,
    get_processing_status,
    get_video_parts,
    process_and_persist_video,
    resegment_stored_video,
)


LOGGER = logging.getLogger(__name__)


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
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


@app.post(
    "/process-video",
    response_model=ProcessVideoResponse,
    status_code=status.HTTP_200_OK,
)
async def process_video_endpoint(
    request: ProcessVideoRequest,
    session: AsyncSession = Depends(get_database_session),
) -> ProcessVideoResponse:
    """Process and persist one YouTube lesson for the simulated user."""

    try:
        return await process_and_persist_video(session, str(request.url))
    except UnsupportedVideoUrlError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only YouTube URLs are supported.",
        ) from error
    except InvalidVideoUrlError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The YouTube URL does not contain a video identifier.",
        ) from error
    except Exception as error:
        LOGGER.exception(
            "Video processing failed for video_id=%s",
            request.url,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The video could not be processed.",
        ) from error


@app.get(
    "/process-video/{processing_job_id}",
    response_model=ProcessVideoResponse,
)
async def processing_status_endpoint(
    processing_job_id: UUID,
    session: AsyncSession = Depends(get_database_session),
) -> ProcessVideoResponse:
    """Return an existing processing job or its completed transcript."""

    try:
        return await get_processing_status(session, processing_job_id)
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processing job was not found.",
        ) from error


@app.get(
    "/video/{video_id}/parts",
    response_model=VideoPartsResponse,
)
async def video_parts_endpoint(
    video_id: str,
    session: AsyncSession = Depends(get_database_session),
) -> VideoPartsResponse:
    """Return the three learning parts for a completed video."""

    result = await get_video_parts(session, video_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Completed video lesson was not found.",
        )
    return result


@app.post(
    "/video/{video_id}/resegment",
    response_model=ResegmentationResponse,
)
async def resegment_video_endpoint(
    video_id: str,
    session: AsyncSession = Depends(get_database_session),
) -> ResegmentationResponse:
    """Regenerate stored sentence boundaries for a completed video."""

    result = await resegment_stored_video(session, video_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Completed video lesson was not found.",
        )
    return result
