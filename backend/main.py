"""FastAPI application entry point for Prononcia."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator
from uuid import UUID, uuid4

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import dispose_database_engine, get_database_session
from authentication.router import router as auth_router
from video_processing.schemas import (
    ProcessVideoRequest,
    ProcessVideoResponse,
    ResegmentationResponse,
    SaveResultRequest,
    SaveResultResponse,
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
from authentication.dependencies import get_current_user_id
from record_processing.pronunciation import (
    evaluate_recording,
    submit_pronunciation,
)
from record_processing.repository import (
    ALLOWED_AUDIO_TYPES,
    PronunciationInputError,
    save_practice_result,
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

app.include_router(auth_router)


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
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_database_session),
) -> ProcessVideoResponse:
    """Process and persist one YouTube lesson for the signed-in user."""

    try:
        return await process_and_persist_video(
            session,
            str(request.url),
            user_id,
        )
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
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_database_session),
) -> ProcessVideoResponse:
    """Return an existing processing job or its completed transcript."""

    try:
        return await get_processing_status(
            session,
            processing_job_id,
            user_id,
        )
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
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_database_session),
) -> VideoPartsResponse:
    """Return the three learning parts for a completed video."""

    result = await get_video_parts(session, video_id, user_id)
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
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_database_session),
) -> ResegmentationResponse:
    """Regenerate stored sentence boundaries for a completed video."""

    result = await resegment_stored_video(session, video_id, user_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Completed video lesson was not found.",
        )
    return result


@app.post("/submit-pronunciation")
async def submit_pronunciation_endpoint(
    audio: UploadFile = File(...),
    video_id: str = Form(...),
    sequence_number: int = Form(...),
    target_sentence: str = Form(...),
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_database_session),
) -> dict[str, object]:
    """Accept one learner recording and save its evaluation."""

    try:
        return await submit_pronunciation(
            session=session,
            audio=audio,
            video_id=video_id,
            sequence_number=sequence_number,
            target_sentence=target_sentence,
            user_id=user_id,
        )
    except PronunciationInputError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except Exception as error:
        LOGGER.exception("Could not submit pronunciation")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The pronunciation could not be evaluated.",
        ) from error


@app.post("/evaluate-pronunciation")
async def evaluate_pronunciation_endpoint(
    audio: UploadFile = File(...),
    target_sentence: str = Form(...),
) -> dict[str, object]:
    """Evaluate a recording without requiring lesson persistence metadata."""

    content_type = (audio.content_type or "").split(";", 1)[0].strip()
    if content_type.lower() not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The recording must be a supported audio file.",
        )
    if not target_sentence.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The practice sentence is invalid.",
        )

    recording_bytes = await audio.read(settings.max_recording_bytes + 1)
    if not recording_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The recording is empty.",
        )
    if len(recording_bytes) > settings.max_recording_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The recording is too large.",
        )

    recording_path = Path(settings.recording_directory)
    recording_path.mkdir(parents=True, exist_ok=True)
    temporary_path = recording_path / f"{uuid4()}.webm"
    temporary_path.write_bytes(recording_bytes)

    try:
        _, result = evaluate_recording(temporary_path, target_sentence)
        return result
    except Exception as error:
        LOGGER.exception("Could not evaluate pronunciation")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The pronunciation could not be evaluated.",
        ) from error
    finally:
        temporary_path.unlink(missing_ok=True)


@app.post(
    "/save-result",
    response_model=SaveResultResponse,
)
async def save_result_endpoint(
    request: SaveResultRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_database_session),
) -> SaveResultResponse:
    """Save a completed lesson and return its overall learner feedback."""

    try:
        return await save_practice_result(
            session,
            request.video_id,
            user_id,
        )
    except PronunciationInputError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except Exception as error:
        LOGGER.exception("Could not save practice result")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The practice result could not be saved.",
        ) from error
