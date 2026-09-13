"""Application service for processing and persisting a video lesson."""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import UUID

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from video_processing.media import (
    download_media,
    extract_video_id,
    is_permitted_youtube_url,
    load_subtitles,
    transcribe_audio,
    split_into_sentences,
)
from video_processing.repository import (
    find_or_create_processing_record,
    load_completed_result,
    load_processing_record,
    mark_processing_failed,
    save_transcription_result,
)
from video_processing.schemas import (
    ProcessVideoResponse,
    TranscriptSegment,
)


class UnsupportedVideoUrlError(ValueError):
    """Raised when the submitted URL is not a supported YouTube URL."""


class InvalidVideoUrlError(ValueError):
    """Raised when a YouTube URL does not contain a video identifier."""


def build_transcript_segments(
    french_segments,
) -> list[TranscriptSegment]:
    """Create public sentence records from French transcript segments."""

    sentence_targets = [
        sentence
        for segment in french_segments
        for sentence in split_into_sentences(segment)
    ]
    return [
        TranscriptSegment(
            sequence_number=index,
            start_seconds=sentence.start_seconds,
            end_seconds=sentence.end_seconds,
            french=sentence.text,
        )
        for index, sentence in enumerate(sentence_targets, start=1)
    ]


def process_video(url: str) -> ProcessVideoResponse:
    """Create French timestamped segments from subtitles or Whisper."""

    video_id = extract_video_id(url)
    with tempfile.TemporaryDirectory(prefix="prononcia-") as directory:
        output_directory = Path(directory)
        audio_path, subtitle_path, metadata = download_media(
            url,
            output_directory,
        )
        if subtitle_path:
            french_segments, french_transcript = load_subtitles(subtitle_path)
            transcript_source = "french_subtitles"
        elif audio_path:
            french_segments, french_transcript = transcribe_audio(audio_path)
            transcript_source = "whisper"
        else:
            raise RuntimeError("No transcript source was available.")
        segments = build_transcript_segments(french_segments)

    return ProcessVideoResponse(
        video_id=video_id,
        source_url=url,
        duration_seconds=(
            float(metadata["duration"])
            if metadata.get("duration") is not None
            else None
        ),
        transcript={
            "french": french_transcript,
            "english": None,
        },
        segments=segments,
        transcript_source=transcript_source,
        media_source_id="00000000-0000-0000-0000-000000000000",
        processing_job_id="00000000-0000-0000-0000-000000000000",
        transcript_id="00000000-0000-0000-0000-000000000000",
        processing_status="ready",
    )


async def process_and_persist_video(
    session: AsyncSession,
    url: str,
) -> ProcessVideoResponse:
    """Validate, process, persist, and return one video lesson."""

    if not is_permitted_youtube_url(url):
        raise UnsupportedVideoUrlError

    if not extract_video_id(url):
        raise InvalidVideoUrlError

    record, is_new = await find_or_create_processing_record(
        session,
        url,
    )

    if not is_new and record.status == "ready":
        return await load_completed_result(
            session,
            record,
            extract_video_id(url),
        )

    if not is_new:
        return ProcessVideoResponse(
            video_id=extract_video_id(url),
            source_url=url,
            duration_seconds=record.duration_seconds,
            transcript={"french": None, "english": None},
            segments=[],
            transcript_source=record.transcript_source or "pending",
            media_source_id=record.media_source_id,
            processing_job_id=record.processing_job_id,
            transcript_id=record.transcript_id
            or "00000000-0000-0000-0000-000000000000",
            processing_status="processing",
        )

    try:
        result = await run_in_threadpool(process_video, url)
        return await save_transcription_result(
            session,
            result,
            record.media_source_id,
            record.processing_job_id,
        )
    except Exception:
        await mark_processing_failed(
            session,
            record.media_source_id,
            record.processing_job_id,
        )
        raise


async def get_processing_status(
    session: AsyncSession,
    processing_job_id: UUID,
) -> ProcessVideoResponse:
    """Return the current status or completed data for a processing job."""

    record = await load_processing_record(session, processing_job_id)
    if record is None:
        raise LookupError("Processing job was not found.")

    video_id = extract_video_id(record.source_url)
    if record.status == "ready":
        return await load_completed_result(session, record, video_id)

    return ProcessVideoResponse(
        video_id=video_id,
        source_url=record.source_url,
        duration_seconds=record.duration_seconds,
        transcript={"french": None, "english": None},
        segments=[],
        transcript_source=record.transcript_source or "pending",
        media_source_id=record.media_source_id,
        processing_job_id=record.processing_job_id,
        transcript_id=record.transcript_id
        or "00000000-0000-0000-0000-000000000000",
        processing_status=record.status,
    )
