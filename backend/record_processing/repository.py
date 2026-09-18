"""PostgreSQL persistence for pronunciation practice attempts."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from video_processing.media import normalize_transcript_text
from video_processing.repository import SIMULATED_USER_ID


ALLOWED_AUDIO_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mp4",
}


class PronunciationInputError(ValueError):
    """Raised when the submitted sentence does not belong to the lesson."""


async def save_pronunciation_result(
    session: AsyncSession,
    video_id: str,
    sequence_number: int,
    target_sentence: str,
    recording_name: str,
    learner_transcription: str,
    score: int,
    feedback: str,
    missed_words: list[str],
) -> None:
    """Insert a new attempt or update the existing sentence attempt."""

    created_at = datetime.now(timezone.utc)
    async with session.begin():
        target = await _find_target_segment(
            session,
            video_id,
            sequence_number,
            target_sentence,
        )
        await session.execute(
            text(
                """
                SELECT pg_advisory_xact_lock(
                    hashtextextended(
                        :attempt_key,
                        0
                    )
                )
                """
            ),
            {
                "attempt_key": (
                    f"{target['media_source_id']}:{target['segment_id']}"
                ),
            },
        )
        practice_session_id = await _find_or_create_practice_session(
            session,
            target["media_source_id"],
            created_at,
        )
        attempt_id = await _find_attempt(
            session,
            practice_session_id,
            target["segment_id"],
        )

        if attempt_id is None:
            attempt_id = uuid4()
            await _insert_attempt(
                session,
                attempt_id,
                practice_session_id,
                target["segment_id"],
                recording_name,
                learner_transcription,
                score,
                feedback,
                created_at,
            )
        else:
            await _update_attempt(
                session,
                attempt_id,
                recording_name,
                learner_transcription,
                score,
                feedback,
                created_at,
            )

        await _replace_missed_words(session, attempt_id, missed_words)


async def _find_target_segment(
    session: AsyncSession,
    video_id: str,
    sequence_number: int,
    target_sentence: str,
) -> dict[str, UUID]:
    """Find and authorize the requested lesson sentence."""

    result = await session.execute(
        text(
            """
            SELECT media_sources.id AS media_source_id,
                   transcript_segments.id AS segment_id,
                   transcript_segments.text AS stored_sentence
            FROM media_sources
            JOIN transcripts
              ON transcripts.media_source_id = media_sources.id
             AND transcripts.id = (
                 SELECT latest.id FROM transcripts AS latest
                 WHERE latest.media_source_id = media_sources.id
                 ORDER BY latest.created_at DESC LIMIT 1
             )
            JOIN transcript_segments
              ON transcript_segments.transcript_id = transcripts.id
            WHERE media_sources.user_id = :user_id
              AND transcript_segments.sequence_number = :sequence_number
              AND (
                  media_sources.id::text = :video_id
                  OR media_sources.source_url LIKE :video_url
              )
            LIMIT 1
            """
        ),
        {
            "user_id": SIMULATED_USER_ID,
            "sequence_number": sequence_number,
            "video_id": video_id,
            "video_url": f"%{video_id}%",
        },
    )
    target = result.mappings().first()

    if not target:
        raise PronunciationInputError("The practice sentence was not found.")
    if normalize_transcript_text(target["stored_sentence"]) != (
        normalize_transcript_text(target_sentence)
    ):
        raise PronunciationInputError("The practice sentence is invalid.")

    return target


async def _find_or_create_practice_session(
    session: AsyncSession,
    media_source_id: UUID,
    created_at: datetime,
) -> UUID:
    """Reuse the active practice session for this user and source."""

    result = await session.execute(
        text(
            """
            SELECT id FROM practice_sessions
            WHERE user_id = :user_id
              AND media_source_id = :media_source_id
              AND status IN ('started', 'in_progress')
            ORDER BY started_at DESC
            LIMIT 1
            """
        ),
        {
            "user_id": SIMULATED_USER_ID,
            "media_source_id": media_source_id,
        },
    )
    practice_session_id = result.scalar_one_or_none()
    if practice_session_id is not None:
        return practice_session_id

    practice_session_id = uuid4()
    await session.execute(
        text(
            """
            INSERT INTO practice_sessions (
                id, user_id, media_source_id, status, started_at
            )
            VALUES (
                :id, :user_id, :media_source_id, 'in_progress', :started_at
            )
            """
        ),
        {
            "id": practice_session_id,
            "user_id": SIMULATED_USER_ID,
            "media_source_id": media_source_id,
            "started_at": created_at,
        },
    )
    return practice_session_id


async def _find_attempt(
    session: AsyncSession,
    practice_session_id: UUID,
    transcript_segment_id: UUID,
) -> UUID | None:
    """Find the existing attempt for one sentence in this session."""

    result = await session.execute(
        text(
            """
            SELECT id FROM sentence_attempts
            WHERE practice_session_id = :practice_session_id
              AND transcript_segment_id = :transcript_segment_id
            ORDER BY created_at DESC
            LIMIT 1
            FOR UPDATE
            """
        ),
        {
            "practice_session_id": practice_session_id,
            "transcript_segment_id": transcript_segment_id,
        },
    )
    return result.scalar_one_or_none()


async def _insert_attempt(
    session: AsyncSession,
    attempt_id: UUID,
    practice_session_id: UUID,
    transcript_segment_id: UUID,
    recording_name: str,
    learner_transcription: str,
    score: int,
    feedback: str,
    created_at: datetime,
) -> None:
    """Insert the first result for a sentence."""

    await session.execute(
        text(
            """
            INSERT INTO sentence_attempts (
                id, practice_session_id, transcript_segment_id,
                recording_path, learner_transcription, score, feedback,
                created_at
            )
            VALUES (
                :id, :practice_session_id, :transcript_segment_id,
                :recording_path, :learner_transcription, :score, :feedback,
                :created_at
            )
            """
        ),
        {
            "id": attempt_id,
            "practice_session_id": practice_session_id,
            "transcript_segment_id": transcript_segment_id,
            "recording_path": recording_name,
            "learner_transcription": learner_transcription,
            "score": score,
            "feedback": feedback,
            "created_at": created_at,
        },
    )


async def _update_attempt(
    session: AsyncSession,
    attempt_id: UUID,
    recording_name: str,
    learner_transcription: str,
    score: int,
    feedback: str,
    created_at: datetime,
) -> None:
    """Update the existing sentence attempt during a retry."""

    await session.execute(
        text(
            """
            UPDATE sentence_attempts
            SET recording_path = :recording_path,
                learner_transcription = :learner_transcription,
                score = :score,
                feedback = :feedback,
                created_at = :created_at
            WHERE id = :id
            """
        ),
        {
            "id": attempt_id,
            "recording_path": recording_name,
            "learner_transcription": learner_transcription,
            "score": score,
            "feedback": feedback,
            "created_at": created_at,
        },
    )


async def _replace_missed_words(
    session: AsyncSession,
    attempt_id: UUID,
    missed_words: list[str],
) -> None:
    """Replace missed words so retries cannot leave stale feedback."""

    await session.execute(
        text(
            """
            DELETE FROM sentence_attempt_missed_words
            WHERE sentence_attempt_id = :sentence_attempt_id
            """
        ),
        {"sentence_attempt_id": attempt_id},
    )
    for word in missed_words:
        await session.execute(
            text(
                """
                INSERT INTO sentence_attempt_missed_words (
                    id, sentence_attempt_id, word
                )
                VALUES (:id, :sentence_attempt_id, :word)
                """
            ),
            {
                "id": uuid4(),
                "sentence_attempt_id": attempt_id,
                "word": word,
            },
        )
