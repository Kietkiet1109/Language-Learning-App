"""Media download, subtitle parsing, and French transcription services."""

from __future__ import annotations

import logging
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pysubs2
from yt_dlp import YoutubeDL

from config import settings
from video_processing.schemas import TranscriptWord, WhisperSegment


LOGGER = logging.getLogger(__name__)
MAX_SENTENCE_WORDS = 28
MAX_SENTENCE_DURATION_SECONDS = 12.0
MAX_HARD_SENTENCE_WORDS = 42
MAX_HARD_SENTENCE_DURATION_SECONDS = 18.0
MIN_SENTENCE_PAUSE_SECONDS = 0.8
MIN_WORDS_FOR_PAUSE_BOUNDARY = 3
SUBTITLE_OVERLAP_TOLERANCE_SECONDS = 0.25
DUPLICATE_GAP_TOLERANCE_SECONDS = 0.75
FRENCH_ABBREVIATIONS = {
    "av",
    "c",
    "dr",
    "etc",
    "mme",
    "mlle",
    "m",
    "p",
    "pr",
}
NON_SPEECH_CUE_PATTERN = re.compile(
    r"(?:\[[^\]]+\]|\([^\)]+\))",
    re.IGNORECASE,
)
NON_SPEECH_CUE_WORDS = {
    "applaudissements",
    "bruit",
    "bruits",
    "musique",
    "rires",
    "silence",
}


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
    """Download and convert the source audio for Whisper transcription."""

    output_template = str(output_directory / "source.%(ext)s")

    options = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "noplaylist": True,
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "fragment_retries": 3,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            }
        ],
    }

    with YoutubeDL(options) as downloader:
        metadata = downloader.extract_info(url, download=True)

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
        condition_on_previous_text=False,
        vad_filter=True,
        word_timestamps=True,
    )
    whisper_segments = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue

        contains_non_speech = has_non_speech_cue(text)
        words = [
            TranscriptWord(
                text=word.word.strip(),
                start_seconds=float(word.start),
                end_seconds=float(word.end),
            )
            for word in (segment.words or [])
            if word.word.strip()
            and word.start is not None
            and word.end is not None
        ]
        whisper_segments.append(
            WhisperSegment(
                text=text,
                start_seconds=float(segment.start),
                end_seconds=float(segment.end),
                words=words,
                is_non_speech=is_pure_non_speech_cue(text),
                contains_non_speech=contains_non_speech,
            )
        )

    for index, segment in enumerate(whisper_segments, start=1):
        LOGGER.debug(
            "whisper_raw index=%d start=%.3f end=%.3f text=%r",
            index,
            segment.start_seconds,
            segment.end_seconds,
            segment.text,
        )
    whisper_segments = remove_adjacent_duplicates(whisper_segments)
    transcript = " ".join(
        segment.text
        for segment in whisper_segments
        if not segment.is_non_speech
    )
    return whisper_segments, transcript


def load_subtitles(subtitle_path: Path) -> tuple[list[WhisperSegment], str]:
    """Read French subtitle events and preserve their timestamps."""

    subtitles = pysubs2.load(str(subtitle_path))
    segments = []
    for event in subtitles:
        text = clean_transcript_text(event.text)
        if text:
            segments.append(
                WhisperSegment(
                    text=text,
                    start_seconds=event.start / 1000,
                    end_seconds=event.end / 1000,
                    is_non_speech=is_pure_non_speech_cue(text),
                    contains_non_speech=has_non_speech_cue(text),
                )
            )

    for index, segment in enumerate(segments, start=1):
        LOGGER.debug(
            "subtitle_raw index=%d start=%.3f end=%.3f text=%r",
            index,
            segment.start_seconds,
            segment.end_seconds,
            segment.text,
        )
    segments = merge_overlapping_subtitles(segments)
    segments = remove_adjacent_duplicates(segments)
    transcript = " ".join(
        segment.text for segment in segments if not segment.is_non_speech
    )
    return segments, transcript


def clean_transcript_text(value: str) -> str:
    """Normalize subtitle markup, Unicode, and whitespace for processing."""

    normalized_value = unicodedata.normalize("NFKC", value)
    normalized_value = re.sub(r"\{.*?\}|<.*?>", "", normalized_value)
    normalized_value = normalized_value.replace("\\N", " ")
    normalized_value = normalized_value.replace("’", "'")
    return re.sub(r"\s+", " ", normalized_value).strip()


def has_non_speech_cue(value: str) -> bool:
    """Return whether text contains a bracketed or parenthesized cue."""

    for match in NON_SPEECH_CUE_PATTERN.finditer(value):
        cue = match.group(0)
        if cue.startswith("["):
            return True
        cue_words = normalize_transcript_text(cue).split()
        if any(word in NON_SPEECH_CUE_WORDS for word in cue_words):
            return True
    return False


def is_pure_non_speech_cue(value: str) -> bool:
    """Return whether an event contains only a known non-speech cue."""

    matches = NON_SPEECH_CUE_PATTERN.findall(value)
    if not matches:
        return False

    remainder = NON_SPEECH_CUE_PATTERN.sub("", value).strip()
    if remainder:
        return False

    cue_words = normalize_transcript_text(" ".join(matches)).split()
    return any(word in NON_SPEECH_CUE_WORDS for word in cue_words)


def normalize_transcript_text(value: str) -> str:
    """Create comparison text without changing display text."""

    normalized_value = clean_transcript_text(value).casefold()
    normalized_value = re.sub(r"[^\w\s']", "", normalized_value)
    return re.sub(r"\s+", " ", normalized_value).strip()


def _text_tokens(value: str) -> list[str]:
    """Return words used for overlap and duplicate comparisons."""

    return clean_transcript_text(value).split()


def _normalized_tokens(value: str) -> list[str]:
    """Return normalized words used for overlap and duplicate comparisons."""

    return normalize_transcript_text(value).split()


def merge_overlapping_text(left: str, right: str) -> str:
    """Merge repeated suffix/prefix words from adjacent text units."""

    left_tokens = _text_tokens(left)
    right_tokens = _text_tokens(right)
    left_normalized = _normalized_tokens(left)
    right_normalized = _normalized_tokens(right)

    max_overlap = min(len(left_tokens), len(right_tokens))
    for overlap in range(max_overlap, 0, -1):
        if left_normalized[-overlap:] == right_normalized[:overlap]:
            return " ".join(left_tokens + right_tokens[overlap:])

    return " ".join(left_tokens + right_tokens)


def merge_overlapping_subtitles(
    segments: list[WhisperSegment],
) -> list[WhisperSegment]:
    """Merge subtitle cues that repeat or overlap the same spoken text."""

    merged_segments: list[WhisperSegment] = []
    for segment in segments:
        if not merged_segments:
            merged_segments.append(segment)
            continue

        previous = merged_segments[-1]
        gap = segment.start_seconds - previous.end_seconds
        same_text = normalize_transcript_text(
            previous.text
        ) == normalize_transcript_text(segment.text)
        overlaps = (
            segment.start_seconds
            < previous.end_seconds - SUBTITLE_OVERLAP_TOLERANCE_SECONDS
        )

        if same_text and gap <= DUPLICATE_GAP_TOLERANCE_SECONDS:
            merged_segments[-1] = previous.model_copy(
                update={
                    "end_seconds": max(
                        previous.end_seconds,
                        segment.end_seconds,
                    ),
                    "contains_non_speech": (
                        previous.contains_non_speech
                        or segment.contains_non_speech
                    ),
                    "is_non_speech": (
                        previous.is_non_speech and segment.is_non_speech
                    ),
                }
            )
            continue

        if overlaps:
            merged_text = merge_overlapping_text(
                previous.text,
                segment.text,
            )
            merged_normalized = normalize_transcript_text(merged_text)
            previous_normalized = normalize_transcript_text(previous.text)
            if merged_normalized != previous_normalized:
                merged_segments[-1] = previous.model_copy(
                    update={
                        "text": merged_text,
                        "end_seconds": max(
                            previous.end_seconds,
                            segment.end_seconds,
                        ),
                        "contains_non_speech": (
                            previous.contains_non_speech
                            or segment.contains_non_speech
                        ),
                        "is_non_speech": False,
                    }
                )
                continue

        merged_segments.append(segment)

    return merged_segments


def remove_adjacent_duplicates(
    segments: list[WhisperSegment],
) -> list[WhisperSegment]:
    """Remove repeated units that overlap or occur almost simultaneously."""

    deduplicated: list[WhisperSegment] = []
    for segment in segments:
        if not deduplicated:
            deduplicated.append(segment)
            continue

        previous = deduplicated[-1]
        is_duplicate = (
            normalize_transcript_text(previous.text)
            == normalize_transcript_text(segment.text)
            and segment.start_seconds
            <= previous.end_seconds + DUPLICATE_GAP_TOLERANCE_SECONDS
        )
        if is_duplicate:
            deduplicated[-1] = previous.model_copy(
                update={
                    "end_seconds": max(
                        previous.end_seconds,
                        segment.end_seconds,
                    ),
                    "contains_non_speech": (
                        previous.contains_non_speech
                        or segment.contains_non_speech
                    ),
                    "is_non_speech": (
                        previous.is_non_speech and segment.is_non_speech
                    ),
                }
            )
            continue

        deduplicated.append(segment)

    return deduplicated


def _remove_repeated_phrase(
    words: list[TranscriptWord],
) -> list[TranscriptWord]:
    """Collapse a suspicious repeated phrase in one candidate sentence."""

    normalized = [normalize_transcript_text(word.text) for word in words]
    for phrase_length in range(min(12, len(words) // 2), 4, -1):
        for start in range(len(words) - phrase_length * 2 + 1):
            first = normalized[start:start + phrase_length]
            second_start = start + phrase_length
            second = normalized[
                second_start:second_start + phrase_length
            ]
            if first != second or not all(first):
                continue

            first_end = words[second_start - 1].end_seconds
            second_start_time = words[second_start].start_seconds
            if second_start_time - first_end > 1.0:
                continue

            LOGGER.warning(
                "repeated_phrase_removed text=%r",
                " ".join(
                    word.text
                    for word in words[second_start:second_start
                                         + phrase_length]
                ),
            )
            return words[:second_start] + words[second_start + phrase_length:]

    return words


def _tokens_from_segment(
    segment: WhisperSegment,
) -> list[TranscriptWord]:
    """Use word timestamps or create a clearly marked fallback timing."""

    if segment.words:
        return segment.words

    words = _text_tokens(segment.text)
    if not words:
        return []

    duration = max(segment.end_seconds - segment.start_seconds, 0.0)
    word_duration = duration / len(words)
    return [
        TranscriptWord(
            text=word,
            start_seconds=segment.start_seconds + index * word_duration,
            end_seconds=segment.start_seconds
            + (index + 1) * word_duration,
        )
        for index, word in enumerate(words)
    ]


def _is_sentence_boundary(word: str) -> bool:
    """Return whether a word ends with a French sentence boundary."""

    stripped_word = re.sub(r"[\"'»”\)\]}]+$", "", word).strip()
    if not stripped_word:
        return False

    if stripped_word[-1] not in ".!?…":
        return False

    if stripped_word.endswith("."):
        abbreviation = normalize_transcript_text(stripped_word[:-1])
        if abbreviation in FRENCH_ABBREVIATIONS:
            return False

    return True


def assemble_into_sentences(
    segments: list[WhisperSegment],
) -> list[WhisperSegment]:
    """Assemble complete sentences across raw timed transcription units."""

    speech_segments = [
        segment for segment in segments if not segment.is_non_speech
    ]
    words = [
        word
        for segment in speech_segments
        for word in _tokens_from_segment(segment)
        if word.text.strip()
    ]
    sentence_segments: list[WhisperSegment] = []
    current_words: list[TranscriptWord] = []

    for index, word in enumerate(words):
        current_words.append(word)
        next_word = words[index + 1] if index + 1 < len(words) else None
        pause_duration = (
            next_word.start_seconds - word.end_seconds
            if next_word is not None
            else 0.0
        )
        sentence_duration = (
            word.end_seconds - current_words[0].start_seconds
        )
        soft_limit = (
            len(current_words) >= MAX_SENTENCE_WORDS
            or sentence_duration >= MAX_SENTENCE_DURATION_SECONDS
        )
        hard_limit = (
            len(current_words) >= MAX_HARD_SENTENCE_WORDS
            or sentence_duration >= MAX_HARD_SENTENCE_DURATION_SECONDS
        )
        pause_boundary = (
            pause_duration >= MIN_SENTENCE_PAUSE_SECONDS
            and len(current_words) >= MIN_WORDS_FOR_PAUSE_BOUNDARY
        )
        should_finish = (
            _is_sentence_boundary(word.text)
            or pause_boundary
            or hard_limit
            or (soft_limit and next_word is None)
        )

        if not should_finish:
            continue

        candidate_words = _remove_repeated_phrase(current_words)
        if candidate_words and not _candidate_is_contaminated(
            candidate_words,
            segments,
        ):
            sentence_segments.append(
                WhisperSegment(
                    text=" ".join(item.text for item in candidate_words),
                    start_seconds=candidate_words[0].start_seconds,
                    end_seconds=candidate_words[-1].end_seconds,
                    words=candidate_words.copy(),
                )
            )
        current_words.clear()

    if current_words:
        candidate_words = _remove_repeated_phrase(current_words)
        if candidate_words and not _candidate_is_contaminated(
            candidate_words,
            segments,
        ):
            sentence_segments.append(
                WhisperSegment(
                    text=" ".join(item.text for item in candidate_words),
                    start_seconds=candidate_words[0].start_seconds,
                    end_seconds=candidate_words[-1].end_seconds,
                    words=candidate_words.copy(),
                )
            )

    return remove_adjacent_duplicates(sentence_segments)


def _candidate_is_contaminated(
    words: list[TranscriptWord],
    raw_segments: list[WhisperSegment],
) -> bool:
    """Reject a candidate containing an embedded non-speech event."""

    start_seconds = words[0].start_seconds
    end_seconds = words[-1].end_seconds
    for segment in raw_segments:
        if not segment.contains_non_speech:
            continue
        if segment.is_non_speech:
            inside_candidate = (
                segment.start_seconds > start_seconds
                and segment.end_seconds < end_seconds
            )
        else:
            inside_candidate = (
                segment.start_seconds <= end_seconds
                and segment.end_seconds >= start_seconds
            )
        if inside_candidate:
            LOGGER.warning(
                "contaminated_sentence_dropped start=%.3f end=%.3f "
                "cue=%r",
                start_seconds,
                end_seconds,
                segment.text,
            )
            return True
    return False
