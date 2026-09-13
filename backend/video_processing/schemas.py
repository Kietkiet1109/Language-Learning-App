"""Pydantic schemas used by the video processing feature."""

from __future__ import annotations
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl


class ProcessVideoRequest(BaseModel):
    """Input required to create a pronunciation lesson."""

    url: HttpUrl = Field(..., description="A permitted YouTube video URL")


class TranscriptSegment(BaseModel):
    """One timestamped sentence in the generated lesson."""

    sequence_number: int
    start_seconds: float
    end_seconds: float
    french: str
    english: str | None = None


class ProcessVideoResponse(BaseModel):
    """Processed video metadata and sentence-level transcripts."""

    video_id: str
    source_url: str
    duration_seconds: float | None
    transcript: dict[str, str | None]
    segments: list[TranscriptSegment]
    transcript_source: str
    media_source_id: UUID
    processing_job_id: UUID
    transcript_id: UUID
    processing_status: str


class WhisperSegment(BaseModel):
    """Small internal representation of a Whisper segment."""

    text: str
    start_seconds: float
    end_seconds: float
