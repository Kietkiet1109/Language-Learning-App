"""Application service for processing and persisting a video lesson."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from uuid import UUID

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from video_processing.media import (
    assemble_into_sentences,
    download_media,
    extract_video_id,
    is_permitted_youtube_url,
    normalize_transcript_text,
    transcribe_audio,
)
from video_processing.repository import (
    find_or_create_processing_record,
    load_completed_result,
    load_resegmentation_record,
    load_transcript_segments,
    load_video_parts,
    load_processing_record,
    mark_processing_failed,
    save_resegmented_transcript,
    save_transcription_result,
)
from video_processing.schemas import (
    ProcessVideoResponse,
    ResegmentationResponse,
    TranscriptSegment,
    VideoPart,
    VideoPartsResponse,
)
from video_processing.translation import translate_segments


LOGGER = logging.getLogger(__name__)


class UnsupportedVideoUrlError(ValueError):
    """Raised when the submitted URL is not a supported YouTube URL."""


class InvalidVideoUrlError(ValueError):
    """Raised when a YouTube URL does not contain a video identifier."""


def build_transcript_segments(
    french_segments,
) -> list[TranscriptSegment]:
    """Create public sentence records from French transcript segments."""

    sentence_targets = assemble_into_sentences(french_segments)
    return [
        TranscriptSegment(
            sequence_number=index,
            start_seconds=sentence.start_seconds,
            end_seconds=sentence.end_seconds,
            french=sentence.text,
        )
        for index, sentence in enumerate(sentence_targets, start=1)
    ]


def translate_transcript_segments(
    segments: list[TranscriptSegment],
) -> list[TranscriptSegment]:
    """Translate each finalized sentence without changing its timing."""

    return translate_segments(segments)


def log_segmentation_diagnostics(
    source_type: str,
    raw_segments,
    final_segments: list[TranscriptSegment],
) -> None:
    """Log raw units and final sentences for segmentation diagnosis."""

    LOGGER.info(
        "segmentation_diagnostics source=%s raw_count=%d final_count=%d",
        source_type,
        len(raw_segments),
        len(final_segments),
    )
    for index, segment in enumerate(raw_segments, start=1):
        LOGGER.debug(
            "segmentation_raw source=%s index=%d start=%.3f end=%.3f "
            "normalized=%r text=%r",
            source_type,
            index,
            segment.start_seconds,
            segment.end_seconds,
            normalize_transcript_text(segment.text),
            segment.text,
        )
    for segment in final_segments:
        LOGGER.debug(
            "segmentation_final sequence=%d start=%.3f end=%.3f "
            "normalized=%r text=%r",
            segment.sequence_number,
            segment.start_seconds,
            segment.end_seconds,
            normalize_transcript_text(segment.french),
            segment.french,
        )


def build_video_parts(
    video_id: str,
    media_source_id: UUID,
    source_url: str,
    duration_seconds: float,
    language_code: str,
    transcript_source: str,
    segments: list[TranscriptSegment],
) -> VideoPartsResponse:
    """Build the three learning modes from stored transcript segments."""

    part_window = VideoPart(
        part_number=1,
        mode="listening",
        title="Listening",
        start_seconds=0,
        end_seconds=duration_seconds,
        show_transcript=True,
        pause_after_segment=False,
        record_audio=False,
        show_translation=False,
        segments=segments,
    )
    repeat_window = part_window.model_copy(
        update={
            "part_number": 2,
            "mode": "repeat_and_evaluate",
            "title": "Repeat and evaluate",
            "pause_after_segment": True,
            "record_audio": True,
            "show_translation": True,
        }
    )
    audio_window = part_window.model_copy(
        update={
            "part_number": 3,
            "mode": "audio_only",
            "title": "Audio-only practice",
            "show_transcript": False,
            "segments": [],
        }
    )
    return VideoPartsResponse(
        video_id=video_id,
        media_source_id=media_source_id,
        source_url=source_url,
        duration_seconds=duration_seconds,
        language_code=language_code,
        transcript_source=transcript_source,
        parts=[part_window, repeat_window, audio_window],
    )


async def get_video_parts(
    session: AsyncSession,
    video_id: str,
) -> VideoPartsResponse | None:
    """Return the stored three-part learning structure for a video."""

    record = await load_video_parts(session, video_id)
    if record is None:
        return None

    stored_video_id = extract_video_id(record.source_url)
    return build_video_parts(
        video_id=stored_video_id or video_id,
        media_source_id=record.media_source_id,
        source_url=record.source_url,
        duration_seconds=record.duration_seconds,
        language_code=record.language_code,
        transcript_source=record.transcript_source,
        segments=record.segments,
    )


async def resegment_stored_video(
    session: AsyncSession,
    video_id: str,
) -> ResegmentationResponse | None:
    """Regenerate and compare sentence segments for a stored video."""

    record = await load_resegmentation_record(session, video_id)
    if record is None or record.transcript_id is None:
        return None

    old_segments = await load_transcript_segments(
        session,
        record.transcript_id,
    )
    result = await run_in_threadpool(process_video, record.source_url)
    new_segments = result.segments
    old_signature = [
        (
            normalize_transcript_text(segment.french),
            round(segment.start_seconds, 3),
            round(segment.end_seconds, 3),
        )
        for segment in old_segments
    ]
    new_signature = [
        (
            normalize_transcript_text(segment.french),
            round(segment.start_seconds, 3),
            round(segment.end_seconds, 3),
        )
        for segment in new_segments
    ]
    new_transcript_id = await save_resegmented_transcript(
        session,
        record.media_source_id,
        new_segments,
        result.transcript["french"] or "",
        result.transcript_source,
    )

    return ResegmentationResponse(
        video_id=extract_video_id(record.source_url) or video_id,
        transcript_id=new_transcript_id,
        old_segment_count=len(old_segments),
        new_segment_count=len(new_segments),
        changed=old_signature != new_signature,
        old_preview=[segment.french for segment in old_segments[:5]],
        new_preview=[segment.french for segment in new_segments[:5]],
    )


def process_video(url: str) -> ProcessVideoResponse:
    """Create French timestamped segments from Whisper audio transcription."""

    video_id = extract_video_id(url)
    with tempfile.TemporaryDirectory(prefix="prononcia-") as directory:
        output_directory = Path(directory)
        audio_path, _, metadata = download_media(
            url,
            output_directory,
        )
        if audio_path:
            french_segments, french_transcript = transcribe_audio(audio_path)
            transcript_source = "whisper"
        else:
            raise RuntimeError("No transcript source was available.")
        segments = build_transcript_segments(french_segments)
        segments = translate_transcript_segments(segments)
        log_segmentation_diagnostics(
            transcript_source,
            french_segments,
            segments,
        )

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
            "english": " ".join(
                segment.english or "" for segment in segments
            ).strip(),
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
        if record.transcript_source == "french_subtitles":
            result = await run_in_threadpool(process_video, url)
            transcript_id = await save_resegmented_transcript(
                session,
                record.media_source_id,
                result.segments,
                result.transcript["french"] or "",
                result.transcript_source,
            )
            return result.model_copy(
                update={
                    "media_source_id": record.media_source_id,
                    "processing_job_id": record.processing_job_id,
                    "transcript_id": transcript_id,
                }
            )
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
