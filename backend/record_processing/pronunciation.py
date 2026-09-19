"""Accept learner audio and transcribe it for pronunciation evaluation."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from record_processing.evaluation import evaluate_transcription
from record_processing.repository import (
    ALLOWED_AUDIO_TYPES,
    PronunciationInputError,
    save_pronunciation_result,
)
from video_processing.media import transcribe_audio


async def submit_pronunciation(
    session: AsyncSession,
    audio: UploadFile,
    video_id: str,
    sequence_number: int,
    target_sentence: str,
    user_id: UUID,
) -> dict[str, object]:
    """Save audio temporarily, transcribe it, evaluate it, and persist it."""

    content_type = (audio.content_type or "").split(";", 1)[0].strip()
    if content_type.lower() not in ALLOWED_AUDIO_TYPES:
        raise PronunciationInputError(
            "The recording must be a supported audio file."
        )

    if not target_sentence.strip() or sequence_number < 1:
        raise PronunciationInputError("The practice sentence is invalid.")

    recording_bytes = await audio.read(settings.max_recording_bytes + 1)
    if not recording_bytes:
        raise PronunciationInputError("The recording is empty.")
    if len(recording_bytes) > settings.max_recording_bytes:
        raise PronunciationInputError("The recording is too large.")

    recording_directory = Path(settings.recording_directory)
    recording_directory.mkdir(parents=True, exist_ok=True)
    recording_name = f"{uuid4()}.webm"
    recording_path = recording_directory / recording_name
    recording_path.write_bytes(recording_bytes)

    learner_transcription, result = evaluate_recording(
        recording_path,
        target_sentence,
    )
    await save_pronunciation_result(
        session=session,
        video_id=video_id,
        sequence_number=sequence_number,
        target_sentence=target_sentence,
        recording_name=recording_name,
        learner_transcription=learner_transcription,
        score=result["score"],
        feedback=result["feedback"],
        missed_words=result["missed_words"],
        user_id=user_id,
    )
    return result


def evaluate_recording(
    recording_path: Path,
    target_sentence: str,
) -> tuple[str, dict[str, object]]:
    """Transcribe one recording and evaluate it against its target sentence."""

    _, learner_transcription = transcribe_audio(recording_path)
    result = evaluate_transcription(target_sentence, learner_transcription)
    return learner_transcription, result
