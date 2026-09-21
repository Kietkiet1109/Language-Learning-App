"""Cloud Run Job entry point for video processing."""

from __future__ import annotations

import asyncio
import logging
import os
from uuid import UUID

from database import dispose_database_engine, session_factory
from video_processing.repository import (
    claim_processing_job,
    mark_processing_failed,
    save_transcription_result,
)
from video_processing.service import process_video


LOGGER = logging.getLogger(__name__)


async def process_job(job_id: UUID) -> None:
    """Claim and process one PostgreSQL video-processing job."""

    async with session_factory() as session:
        record = await claim_processing_job(session, job_id)

    if record is None:
        LOGGER.info("worker_job_not_claimed job_id=%s", job_id)
        return

    try:
        result = await asyncio.to_thread(process_video, record.source_url)
        async with session_factory() as session:
            await save_transcription_result(
                session,
                result,
                record.media_source_id,
                record.processing_job_id,
            )
        LOGGER.info("worker_job_completed job_id=%s", job_id)
    except Exception:
        async with session_factory() as session:
            await mark_processing_failed(
                session,
                record.media_source_id,
                record.processing_job_id,
            )
        LOGGER.exception("worker_job_failed job_id=%s", job_id)
        raise


async def run_worker() -> None:
    """Run the job identified by the Cloud Run environment."""

    raw_job_id = os.environ.get("PRONONCIA_JOB_ID")
    if not raw_job_id:
        raise RuntimeError("PRONONCIA_JOB_ID is not configured.")

    try:
        job_id = UUID(raw_job_id)
    except ValueError as exc:
        raise RuntimeError("PRONONCIA_JOB_ID must be a UUID.") from exc

    try:
        await process_job(job_id)
    finally:
        await dispose_database_engine()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())
