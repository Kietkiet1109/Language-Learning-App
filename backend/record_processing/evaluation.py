"""Evaluate learner transcriptions against target sentences."""

from __future__ import annotations

from rapidfuzz import fuzz

from video_processing.media import normalize_transcript_text


def evaluate_transcription(
    target_sentence: str,
    learner_transcription: str,
) -> dict[str, object]:
    """Return a text-based score, missed words, and feedback."""

    target_words = normalize_transcript_text(target_sentence).split()
    learner_words = normalize_transcript_text(learner_transcription).split()
    score = round(fuzz.ratio(target_sentence, learner_transcription))
    missed_words = [word for word in target_words if word not in learner_words]

    if score >= 90:
        feedback = "Excellent repetition. Keep this clear pronunciation."
    elif score >= 70:
        feedback = "Good attempt. Repeat the missed words a little more clearly."
    else:
        feedback = "Listen once more, then repeat the sentence slowly."

    return {
        "score": score,
        "learner_transcription": learner_transcription,
        "missed_words": missed_words,
        "feedback": feedback,
    }
