"""PostgreSQL persistence for processed video lessons."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from video_processing.media import normalize_transcript_text
from video_processing.schemas import (
    ProcessVideoResponse,
    TranscriptSegment,
)


SIMULATED_USER_ID = UUID("00000000-0000-0000-0000-000000000000")
SIMULATED_USER_NAME = "Kiet Ngo"
SIMULATED_USER_EMAIL = "kiet@prononcia.com"


@dataclass(frozen=True)
class ProcessingRecord:
    """Database identifiers and state for one processing request."""

    media_source_id: UUID
    processing_job_id: UUID
    transcript_id: UUID | None
    source_url: str
    status: str
    duration_seconds: float | None
    transcript_source: str | None


@dataclass(frozen=True)
class VideoPartsRecord:
    """Stored media and transcript data for learning-part construction."""

    media_source_id: UUID
    source_url: str
    duration_seconds: float
    language_code: str
    transcript_source: str
    segments: list[TranscriptSegment]


async def find_or_create_processing_record(
    session: AsyncSession,
    source_url: str,
) -> tuple[ProcessingRecord, bool]:
    """Reuse an active/ready record or create a new processing record."""

    async with session.begin():
        await session.execute(
            text(
                """
                SELECT pg_advisory_xact_lock(
                    hashtextextended(:source_url, 0)
                )
                """
            ),
            {"source_url": source_url},
        )
        existing = (
            await session.execute(
                text(
                    """
                    SELECT
                        media_sources.id AS media_source_id,
                        media_processing_jobs.id AS processing_job_id,
                        transcripts.id AS transcript_id,
                        media_sources.source_url,
                        media_sources.status AS source_status,
                        media_processing_jobs.status AS job_status,
                        media_sources.duration_seconds,
                        transcripts.transcription_model
                    FROM media_sources
                    JOIN media_processing_jobs
                        ON media_processing_jobs.media_source_id =
                           media_sources.id
                    LEFT JOIN transcripts
                        ON transcripts.media_source_id = media_sources.id
                       AND transcripts.id = (
                           SELECT latest_transcript.id
                           FROM transcripts AS latest_transcript
                           WHERE latest_transcript.media_source_id =
                                 media_sources.id
                           ORDER BY latest_transcript.created_at DESC
                           LIMIT 1
                       )
                    WHERE media_sources.user_id = :user_id
                      AND media_sources.source_url = :source_url
                      AND (
                          (
                              media_sources.status = 'ready'
                              AND transcripts.id IS NOT NULL
                          )
                          OR media_sources.status = 'processing'
                          OR media_processing_jobs.status IN (
                              'pending', 'running'
                          )
                      )
                    ORDER BY
                        CASE
                            WHEN media_sources.status = 'ready' THEN 0
                            WHEN media_processing_jobs.status IN (
                                'pending', 'running'
                            ) THEN 1
                            ELSE 2
                        END,
                        media_sources.created_at DESC
                    LIMIT 1
                    """
                ),
                {
                    "user_id": SIMULATED_USER_ID,
                    "source_url": source_url,
                },
            )
        ).mappings().first()

        if existing:
            status = (
                "ready"
                if existing["source_status"] == "ready"
                else "processing"
            )
            return (
                ProcessingRecord(
                    media_source_id=existing["media_source_id"],
                    processing_job_id=existing["processing_job_id"],
                    transcript_id=existing["transcript_id"],
                    source_url=existing["source_url"],
                    status=status,
                    duration_seconds=existing["duration_seconds"],
                    transcript_source=existing["transcription_model"],
                ),
                False,
            )

        media_source_id = uuid4()
        processing_job_id = uuid4()
        created_at = datetime.now(timezone.utc)
        await session.execute(
            text(
                """
                INSERT INTO users (
                    id, name, email, is_active, created_at, updated_at
                )
                VALUES (
                    :user_id, :user_name, :user_email, TRUE,
                    :created_at, :created_at
                )
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "user_id": SIMULATED_USER_ID,
                "user_name": SIMULATED_USER_NAME,
                "user_email": SIMULATED_USER_EMAIL,
                "created_at": created_at,
            },
        )
        await session.execute(
            text(
                """
                INSERT INTO media_sources (
                    id, user_id, source_url, source_type, language_code,
                    status, created_at
                )
                VALUES (
                    :source_id, :user_id, :source_url, 'youtube', 'fr',
                    'processing', :created_at
                )
                """
            ),
            {
                "source_id": media_source_id,
                "user_id": SIMULATED_USER_ID,
                "source_url": source_url,
                "created_at": created_at,
            },
        )
        await session.execute(
            text(
                """
                INSERT INTO media_processing_jobs (
                    id, media_source_id, job_type, status, attempt_count,
                    started_at, created_at
                )
                VALUES (
                    :job_id, :source_id, 'transcription', 'running', 1,
                    :started_at, :created_at
                )
                """
            ),
            {
                "job_id": processing_job_id,
                "source_id": media_source_id,
                "started_at": created_at,
                "created_at": created_at,
            },
        )
        return (
            ProcessingRecord(
                media_source_id=media_source_id,
                processing_job_id=processing_job_id,
                transcript_id=None,
                source_url=source_url,
                status="processing",
                duration_seconds=None,
                transcript_source=None,
            ),
            True,
        )


async def load_processing_record(
    session: AsyncSession,
    processing_job_id: UUID,
) -> ProcessingRecord | None:
    """Load a processing record for status polling."""

    async with session.begin():
        row = (
            await session.execute(
                text(
                    """
                    SELECT
                        media_sources.id AS media_source_id,
                        media_processing_jobs.id AS processing_job_id,
                        transcripts.id AS transcript_id,
                        media_sources.source_url,
                        media_sources.status AS source_status,
                        media_processing_jobs.status AS job_status,
                        media_sources.duration_seconds,
                        transcripts.transcription_model
                    FROM media_sources
                    JOIN media_processing_jobs
                        ON media_processing_jobs.media_source_id =
                           media_sources.id
                    LEFT JOIN transcripts
                        ON transcripts.media_source_id = media_sources.id
                       AND transcripts.id = (
                           SELECT latest_transcript.id
                           FROM transcripts AS latest_transcript
                           WHERE latest_transcript.media_source_id =
                                 media_sources.id
                           ORDER BY latest_transcript.created_at DESC
                           LIMIT 1
                       )
                    WHERE media_processing_jobs.id = :job_id
                      AND media_sources.user_id = :user_id
                    LIMIT 1
                    """
                ),
                {
                    "job_id": processing_job_id,
                    "user_id": SIMULATED_USER_ID,
                },
            )
        ).mappings().first()

    if not row:
        return None

    status = "ready" if row["source_status"] == "ready" else "processing"
    if row["job_status"] == "failed":
        status = "failed"
    return ProcessingRecord(
        media_source_id=row["media_source_id"],
        processing_job_id=row["processing_job_id"],
        transcript_id=row["transcript_id"],
        source_url=row["source_url"],
        status=status,
        duration_seconds=row["duration_seconds"],
        transcript_source=row["transcription_model"],
    )


async def load_completed_result(
    session: AsyncSession,
    record: ProcessingRecord,
    video_id: str,
) -> ProcessVideoResponse:
    """Load an existing completed transcript and its sentence segments."""

    if record.transcript_id is None:
        raise RuntimeError("Completed processing has no transcript.")

    async with session.begin():
        rows = (
            await session.execute(
                text(
                    """
                    SELECT sequence_number, start_seconds, end_seconds, text,
                           english_text
                    FROM transcript_segments
                    WHERE transcript_id = :transcript_id
                    ORDER BY sequence_number
                    """
                ),
                {"transcript_id": record.transcript_id},
            )
        ).mappings().all()

    segments = [
        TranscriptSegment(
            sequence_number=row["sequence_number"],
            start_seconds=row["start_seconds"],
            end_seconds=row["end_seconds"],
            french=row["text"],
            english=row["english_text"],
        )
        for row in rows
    ]
    return ProcessVideoResponse(
        video_id=video_id,
        source_url=record.source_url,
        duration_seconds=record.duration_seconds,
        transcript={
            "french": " ".join(segment.french for segment in segments),
            "english": " ".join(
                segment.english or "" for segment in segments
            ).strip(),
        },
        segments=segments,
        transcript_source=record.transcript_source or "stored",
        media_source_id=record.media_source_id,
        processing_job_id=record.processing_job_id,
        transcript_id=record.transcript_id,
        processing_status="ready",
    )


async def load_video_parts(
    session: AsyncSession,
    video_id: str,
) -> VideoPartsRecord | None:
    """Load stored timing data used to construct the learning parts."""

    async with session.begin():
        rows = (
            await session.execute(
                text(
                    """
                    SELECT
                        media_sources.id AS media_source_id,
                        media_sources.source_url,
                        media_sources.duration_seconds,
                        transcripts.language_code,
                        transcripts.transcription_model,
                        transcript_segments.sequence_number,
                        transcript_segments.start_seconds,
                        transcript_segments.end_seconds,
                        transcript_segments.text,
                        transcript_segments.english_text
                    FROM media_sources
                    JOIN transcripts
                        ON transcripts.media_source_id = media_sources.id
                       AND transcripts.id = (
                           SELECT latest_transcript.id
                           FROM transcripts AS latest_transcript
                           WHERE latest_transcript.media_source_id =
                                 media_sources.id
                           ORDER BY latest_transcript.created_at DESC
                           LIMIT 1
                       )
                    JOIN transcript_segments
                        ON transcript_segments.transcript_id = transcripts.id
                    WHERE media_sources.user_id = :user_id
                      AND media_sources.status = 'ready'
                      AND (
                          media_sources.id::text = :video_id
                          OR media_sources.source_url LIKE :video_url
                      )
                    ORDER BY transcript_segments.sequence_number
                    """
                ),
                {
                    "user_id": SIMULATED_USER_ID,
                    "video_id": video_id,
                    "video_url": f"%{video_id}%",
                },
            )
        ).mappings().all()

    if not rows:
        return None

    first_row = rows[0]
    segments = [
        TranscriptSegment(
            sequence_number=row["sequence_number"],
            start_seconds=row["start_seconds"],
            end_seconds=row["end_seconds"],
            french=row["text"],
            english=row["english_text"],
        )
        for row in rows
    ]
    duration_seconds = first_row["duration_seconds"]
    if duration_seconds is None:
        duration_seconds = max(
            segment.end_seconds for segment in segments
        )

    return VideoPartsRecord(
        media_source_id=first_row["media_source_id"],
        source_url=first_row["source_url"],
        duration_seconds=float(duration_seconds),
        language_code=first_row["language_code"],
        transcript_source=first_row["transcription_model"] or "stored",
        segments=segments,
    )


async def load_resegmentation_record(
    session: AsyncSession,
    video_id: str,
) -> ProcessingRecord | None:
    """Load the stored source and active transcript for resegmentation."""

    async with session.begin():
        row = (
            await session.execute(
                text(
                    """
                    SELECT
                        media_sources.id AS media_source_id,
                        media_processing_jobs.id AS processing_job_id,
                        transcripts.id AS transcript_id,
                        media_sources.source_url,
                        media_sources.status AS source_status,
                        media_sources.duration_seconds,
                        transcripts.transcription_model
                    FROM media_sources
                    JOIN transcripts
                        ON transcripts.media_source_id = media_sources.id
                    LEFT JOIN media_processing_jobs
                        ON media_processing_jobs.media_source_id =
                           media_sources.id
                    WHERE media_sources.user_id = :user_id
                      AND media_sources.status = 'ready'
                      AND (
                          media_sources.id::text = :video_id
                          OR media_sources.source_url LIKE :video_url
                      )
                    ORDER BY transcripts.created_at DESC
                    LIMIT 1
                    """
                ),
                {
                    "user_id": SIMULATED_USER_ID,
                    "video_id": video_id,
                    "video_url": f"%{video_id}%",
                },
            )
        ).mappings().first()

    if not row:
        return None

    return ProcessingRecord(
        media_source_id=row["media_source_id"],
        processing_job_id=row["processing_job_id"],
        transcript_id=row["transcript_id"],
        source_url=row["source_url"],
        status="ready",
        duration_seconds=row["duration_seconds"],
        transcript_source=row["transcription_model"],
    )


async def load_transcript_segments(
    session: AsyncSession,
    transcript_id: UUID,
) -> list[TranscriptSegment]:
    """Load sentence segments belonging to one transcript version."""

    async with session.begin():
        rows = (
            await session.execute(
                text(
                    """
                    SELECT sequence_number, start_seconds, end_seconds, text,
                           english_text
                    FROM transcript_segments
                    WHERE transcript_id = :transcript_id
                    ORDER BY sequence_number
                    """
                ),
                {"transcript_id": transcript_id},
            )
        ).mappings().all()

    return [
        TranscriptSegment(
            sequence_number=row["sequence_number"],
            start_seconds=row["start_seconds"],
            end_seconds=row["end_seconds"],
            french=row["text"],
            english=row["english_text"],
        )
        for row in rows
    ]


async def save_resegmented_transcript(
    session: AsyncSession,
    media_source_id: UUID,
    segments: list[TranscriptSegment],
    full_text: str,
    transcription_model: str,
) -> UUID:
    """Save a new transcript version without deleting the old version."""

    transcript_id = uuid4()
    created_at = datetime.now(timezone.utc)
    async with session.begin():
        await session.execute(
            text(
                """
                INSERT INTO transcripts (
                    id, media_source_id, language_code, full_text,
                    transcription_model, created_at
                )
                VALUES (
                    :transcript_id, :media_source_id, 'fr', :full_text,
                    :transcription_model, :created_at
                )
                """
            ),
            {
                "transcript_id": transcript_id,
                "media_source_id": media_source_id,
                "full_text": full_text,
                "transcription_model": transcription_model,
                "created_at": created_at,
            },
        )
        for segment in segments:
            await session.execute(
                text(
                    """
                    INSERT INTO transcript_segments (
                        id, transcript_id, sequence_number, text,
                        normalized_text, start_seconds, end_seconds,
                        english_text
                    )
                    VALUES (
                        :segment_id, :transcript_id, :sequence_number,
                        :segment_text, :normalized_text, :start_seconds,
                        :end_seconds, :english_text
                    )
                    """
                ),
                {
                    "segment_id": uuid4(),
                    "transcript_id": transcript_id,
                    "sequence_number": segment.sequence_number,
                    "segment_text": segment.french,
                    "normalized_text": normalize_transcript_text(
                        segment.french
                    ),
                    "start_seconds": segment.start_seconds,
                    "end_seconds": segment.end_seconds,
                    "english_text": segment.english,
                },
            )
    return transcript_id


async def save_transcription_result(
    session: AsyncSession,
    result: ProcessVideoResponse,
    media_source_id: UUID,
    processing_job_id: UUID,
) -> ProcessVideoResponse:
    """Save transcript data and complete the processing transaction."""

    transcript_id = uuid4()
    completed_at = datetime.now(timezone.utc)

    async with session.begin():
        await session.execute(
            text(
                """
                INSERT INTO transcripts (
                    id, media_source_id, language_code, full_text,
                    transcription_model, created_at
                )
                VALUES (
                    :transcript_id, :source_id, 'fr', :full_text,
                    :transcription_model, :created_at
                )
                """
            ),
            {
                "transcript_id": transcript_id,
                "source_id": media_source_id,
                "full_text": result.transcript["french"] or "",
                "transcription_model": result.transcript_source,
                "created_at": completed_at,
            },
        )
        for segment in result.segments:
            await session.execute(
                text(
                    """
                    INSERT INTO transcript_segments (
                        id, transcript_id, sequence_number, text,
                        normalized_text, start_seconds, end_seconds,
                        english_text
                    )
                    VALUES (
                        :segment_id, :transcript_id, :sequence_number,
                        :segment_text, :normalized_text, :start_seconds,
                        :end_seconds, :english_text
                    )
                    """
                ),
                {
                    "segment_id": uuid4(),
                    "transcript_id": transcript_id,
                    "sequence_number": segment.sequence_number,
                    "segment_text": segment.french,
                    "normalized_text": normalize_transcript_text(
                        segment.french
                    ),
                    "start_seconds": segment.start_seconds,
                    "end_seconds": segment.end_seconds,
                    "english_text": segment.english,
                },
            )
        await session.execute(
            text(
                """
                UPDATE media_processing_jobs
                SET status = 'completed', completed_at = :completed_at
                WHERE id = :job_id
                """
            ),
            {
                "job_id": processing_job_id,
                "completed_at": completed_at,
            },
        )
        await session.execute(
            text(
                """
                UPDATE media_sources
                SET status = 'ready', duration_seconds = :duration_seconds
                WHERE id = :source_id
                """
            ),
            {
                "source_id": media_source_id,
                "duration_seconds": result.duration_seconds,
            },
        )

    return result.model_copy(
        update={
            "media_source_id": media_source_id,
            "processing_job_id": processing_job_id,
            "transcript_id": transcript_id,
        }
    )


async def mark_processing_failed(
    session: AsyncSession,
    media_source_id: UUID,
    processing_job_id: UUID,
) -> None:
    """Mark source and job failed without exposing internal diagnostics."""

    async with session.begin():
        await session.execute(
            text(
                """
                UPDATE media_processing_jobs
                SET status = 'failed', error_message = :error_message
                WHERE id = :job_id
                """
            ),
            {
                "job_id": processing_job_id,
                "error_message": "Media processing failed.",
            },
        )
        await session.execute(
            text(
                """
                UPDATE media_sources
                SET status = 'failed'
                WHERE id = :source_id
                """
            ),
            {"source_id": media_source_id},
        )
