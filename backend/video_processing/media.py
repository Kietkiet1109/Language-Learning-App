"""Media download, subtitle parsing, and French transcription services."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from yt_dlp import YoutubeDL

from config import settings
from video_processing.schemas import WhisperSegment


YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
}


def is_permitted_youtube_url(url: str) -> bool:
    """Return whether a URL points to a supported YouTube host."""

    parsed_url = urlparse(url)
    hostname = (parsed_url.hostname or "").lower()
    return (
        parsed_url.scheme in {"http", "https"}
        and hostname in YOUTUBE_HOSTS
    )


def extract_video_id(url: str) -> str:
    """Extract a stable YouTube video identifier from a permitted URL."""

    parsed_url = urlparse(url)
    hostname = (parsed_url.hostname or "").lower()

    if hostname in {"youtu.be", "www.youtu.be"}:
        return parsed_url.path.strip("/").split("/")[0]

    query_values = dict(
        item.split("=", 1)
        for item in parsed_url.query.split("&")
        if "=" in item
    )
    if query_values.get("v"):
        return query_values["v"]

    path_parts = [part for part in parsed_url.path.split("/") if part]
    if path_parts and path_parts[0] in {"shorts", "embed", "live"}:
        return path_parts[1] if len(path_parts) > 1 else ""

    return ""


def find_french_subtitle(
    metadata: dict[str, Any],
) -> tuple[str | None, bool]:
    """Find a French subtitle language and whether it is automatic."""

    for language in metadata.get("subtitles", {}):
        if language.lower().startswith("fr"):
            return language, False

    for language in metadata.get("automatic_captions", {}):
        if language.lower().startswith("fr"):
            return language, True

    return None, False


def download_media(
    url: str,
    output_directory: Path,
) -> tuple[Path | None, Path | None, dict[str, Any]]:
    """Download French subtitles or audio as the fallback."""

    probe_options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with YoutubeDL(probe_options) as downloader:
        metadata = downloader.extract_info(url, download=False)

    subtitle_language, _ = find_french_subtitle(metadata)
    output_template = str(output_directory / "source.%(ext)s")

    if subtitle_language:
        options = {
            "noplaylist": True,
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [subtitle_language],
            "subtitlesformat": "vtt/srt/best",
        }
    else:
        options = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                }
            ],
        }

    with YoutubeDL(options) as downloader:
        downloader.extract_info(url, download=True)

    if subtitle_language:
        subtitle_path = next(
            (
                path
                for path in output_directory.glob("source.*")
                if path.suffix.lower() in {".vtt", ".srt", ".ass"}
            ),
            None,
        )
        if subtitle_path is None:
            raise RuntimeError("French subtitles were not downloaded.")
        return None, subtitle_path, metadata

    audio_path = output_directory / "source.wav"
    if not audio_path.exists():
        raise RuntimeError("FFmpeg did not create the extracted audio file.")

    return audio_path, None, metadata


@lru_cache(maxsize=1)
def load_whisper_model():
    """Create the Whisper model only when processing is first requested."""

    from faster_whisper import WhisperModel

    return WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )


def transcribe_audio(audio_path: Path) -> tuple[list[WhisperSegment], str]:
    """Transcribe French speech and return timestamped segments."""

    model = load_whisper_model()
    segments, _ = model.transcribe(
        str(audio_path),
        language="fr",
        task="transcribe",
        vad_filter=True,
    )
    whisper_segments = [
        WhisperSegment(
            text=segment.text.strip(),
            start_seconds=float(segment.start),
            end_seconds=float(segment.end),
        )
        for segment in segments
        if segment.text.strip()
    ]
    transcript = " ".join(segment.text for segment in whisper_segments)
    return whisper_segments, transcript


def load_subtitles(subtitle_path: Path) -> tuple[list[WhisperSegment], str]:
    """Read French subtitle events and preserve their timestamps."""

    import pysubs2

    subtitles = pysubs2.load(str(subtitle_path))
    segments = []
    for event in subtitles:
        text = re.sub(r"\{.*?\}|<.*?>", "", event.text)
        text = re.sub(r"\\N", " ", text).strip()
        if text:
            segments.append(
                WhisperSegment(
                    text=text,
                    start_seconds=event.start / 1000,
                    end_seconds=event.end / 1000,
                )
            )

    transcript = " ".join(segment.text for segment in segments)
    return segments, transcript


def split_into_sentences(
    segment: WhisperSegment,
) -> list[WhisperSegment]:
    """Split a Whisper segment while preserving approximate timestamps."""

    pieces = [
        piece.strip()
        for piece in re.split(r"(?<=[.!?…])\s+", segment.text)
        if piece.strip()
    ]
    if len(pieces) <= 1:
        return [segment]

    total_characters = max(len(segment.text), 1)
    sentence_segments = []
    cursor = 0
    duration = segment.end_seconds - segment.start_seconds

    for piece in pieces:
        start_ratio = cursor / total_characters
        cursor += len(piece)
        end_ratio = cursor / total_characters
        sentence_segments.append(
            WhisperSegment(
                text=piece,
                start_seconds=segment.start_seconds + duration * start_ratio,
                end_seconds=segment.start_seconds + duration * end_ratio,
            )
        )

    return sentence_segments
