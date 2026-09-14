"""Pydantic schemas used by the video processing feature."""

from __future__ import annotations
from typing import Literal
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


class TranscriptWord(BaseModel):
    """One word with its approximate audio boundaries."""

    text: str
    start_seconds: float
    end_seconds: float


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


class VideoPart(BaseModel):
    """Metadata and transcript visibility rules for one learning part."""

    part_number: Literal[1, 2, 3]
    mode: Literal["listening", "repeat_and_evaluate", "audio_only"]
    title: str
    start_seconds: float
    end_seconds: float
    show_transcript: bool
    pause_after_segment: bool
    record_audio: bool
    show_translation: bool
    segments: list[TranscriptSegment]


class VideoPartsResponse(BaseModel):
    """Three-part learning metadata for a stored video lesson."""

    video_id: str
    media_source_id: UUID
    source_url: str
    duration_seconds: float | None
    language_code: str
    transcript_source: str
    parts: list[VideoPart]


class WhisperSegment(BaseModel):
    """Small internal representation of a Whisper segment."""

    text: str
    start_seconds: float
    end_seconds: float
    words: list[TranscriptWord] = Field(default_factory=list)
    is_non_speech: bool = False
    contains_non_speech: bool = False


class ResegmentationResponse(BaseModel):
    """Comparison returned after replacing stored sentence boundaries."""

    video_id: str
    transcript_id: UUID
    old_segment_count: int
    new_segment_count: int
    changed: bool
    old_preview: list[str]
    new_preview: list[str]
