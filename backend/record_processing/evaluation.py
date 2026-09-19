"""Evaluate learner transcriptions against French target sentences."""

from __future__ import annotations

from difflib import SequenceMatcher
from rapidfuzz import fuzz
from video_processing.media import normalize_transcript_text


MINIMUM_WORD_SIMILARITY = 50


def evaluate_transcription(
    target_sentence: str,
    learner_transcription: str,
) -> dict[str, object]:
    """Return aligned text accuracy, word issues, and constructive feedback.

    The score distributes 100 points across the target words.  Exact words
    receive full credit, near matches receive partial credit, and unrelated
    substitutions receive no credit.  This makes a five-word sentence worth
    approximately 20 points per word.
    """

    normalized_target = normalize_transcript_text(target_sentence)
    normalized_learner = normalize_transcript_text(learner_transcription)
    target_words = normalized_target.split()
    learner_words = normalized_learner.split()

    if not target_words:
        raise ValueError("The target sentence cannot be empty.")

    score = calculate_word_score(target_words, learner_words)

    missed_words, incorrect_words = aligned_word_issues(
        target_words,
        learner_words,
    )
    feedback = build_feedback(score, missed_words, incorrect_words)
    pronunciation_hints = [
        f"Try to pronounce '{word}' more clearly."
        for word in missed_words + incorrect_words
    ]

    return {
        "score": score,
        "analysis_method": "aligned_word_similarity",
        "learner_transcription": learner_transcription,
        "missed_words": missed_words,
        "incorrect_words": incorrect_words,
        "pronunciation_hints": pronunciation_hints,
        "feedback": feedback,
    }


def calculate_word_score(
    target_words: list[str],
    learner_words: list[str],
) -> int:
    """Calculate proportional credit for each target word.

    Dynamic alignment keeps words in their spoken order while allowing a
    short recording to match a target word in the middle of a sentence. A
    replacement is scored with fuzzy word similarity, while deleted target
    words receive zero and inserted learner words receive no extra credit.
    """

    if not target_words:
        return 0

    alignment_scores = [
        [0.0] * (len(learner_words) + 1)
        for _ in range(len(target_words) + 1)
    ]

    for target_index, target_word in enumerate(target_words, start=1):
        for learner_index, learner_word in enumerate(learner_words, start=1):
            similarity = fuzz.ratio(target_word, learner_word)
            word_credit = (
                similarity / 100
                if similarity >= MINIMUM_WORD_SIMILARITY
                else 0.0
            )
            alignment_scores[target_index][learner_index] = max(
                alignment_scores[target_index - 1][learner_index],
                alignment_scores[target_index][learner_index - 1],
                alignment_scores[target_index - 1][learner_index - 1]
                + word_credit,
            )

    total_similarity = alignment_scores[-1][-1]
    return round(total_similarity / len(target_words) * 100)


def aligned_word_issues(
    target_words: list[str],
    learner_words: list[str],
) -> tuple[list[str], list[str]]:
    """Extract missing target words and substitutions from an alignment."""

    missed_words: list[str] = []
    incorrect_words: list[str] = []
    matcher = SequenceMatcher(a=target_words, b=learner_words)

    for tag, target_start, target_end, _, _ in matcher.get_opcodes():
        if tag == "delete":
            missed_words.extend(target_words[target_start:target_end])
        elif tag == "replace":
            incorrect_words.extend(target_words[target_start:target_end])
        elif tag == "insert":
            continue

    return missed_words, incorrect_words


def build_feedback(
    score: int,
    missed_words: list[str],
    incorrect_words: list[str],
) -> str:
    """Build feedback that points to the most useful next practice step."""

    focus_words = missed_words + incorrect_words
    if score == 100 and not focus_words:
        return "Perfect pronunciation."
    elif score >= 90 and not focus_words:
        return "Almost perfect. Keep this clear pronunciation."
    if focus_words:
        words = ", ".join(f"'{word}'" for word in focus_words[:3])
        if missed_words and incorrect_words:
            return f"Review {words}; some words were missed or changed."
        if missed_words:
            return f"Try to pronounce {words} clearly and include every word."
        return f"Listen for the sounds in {words} and repeat them slowly."
    if score >= 70:
        return (
            "Good attempt. Repeat the sentence once more for a clearer match."
        )
    return "Listen once more, then repeat the sentence slowly."


def build_overall_feedback(score: int) -> str:
    """Return session feedback appropriate to the overall accuracy."""

    if score >= 90:
        return (
            "Excellent work! You pronounced almost every sentence correctly."
        )
    if score >= 75:
        return "Good job! You pronounced most sentences correctly."
    if score >= 50:
        return "Good effort! Review the missed sentences and try again."
    return "Keep practicing! Listen carefully and repeat each sentence slowly."
