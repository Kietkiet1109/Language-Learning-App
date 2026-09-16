"""Local OPUS-MT French-to-English translation service."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from config import settings
from video_processing.schemas import TranscriptSegment


LOGGER = logging.getLogger(__name__)
TRANSLATION_BATCH_SIZE = 16


@lru_cache(maxsize=1)
def load_translation_model() -> tuple[Any, Any, torch.device]:
    """Load the local OPUS-MT model once per backend process."""

    tokenizer = AutoTokenizer.from_pretrained(settings.translation_model)
    model = AutoModelForSeq2SeqLM.from_pretrained(
        settings.translation_model,
    )
    device = torch.device(settings.translation_device)
    model.to(device)
    model.eval()
    LOGGER.info(
        "translation_model_loaded model=%s device=%s",
        settings.translation_model,
        device,
    )
    return tokenizer, model, device


def translate_segments(
    segments: list[TranscriptSegment],
) -> list[TranscriptSegment]:
    """Translate finalized French learning segments locally."""

    if not segments:
        return []

    tokenizer, model, device = load_translation_model()
    translated_segments: list[TranscriptSegment] = []

    for start in range(0, len(segments), TRANSLATION_BATCH_SIZE):
        batch = segments[start:start + TRANSLATION_BATCH_SIZE]
        encoded = tokenizer(
            [segment.french for segment in batch],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=256,
        ).to(device)
        with torch.inference_mode():
            generated_tokens = model.generate(
                **encoded,
                max_new_tokens=128,
                num_beams=4,
            )
        english_texts = tokenizer.batch_decode(
            generated_tokens,
            skip_special_tokens=True,
        )

        for segment, english in zip(batch, english_texts):
            translation = english.strip()
            if not translation:
                raise RuntimeError(
                    "The local translation model returned empty text."
                )
            translated_segments.append(
                segment.model_copy(update={"english": translation})
            )
            LOGGER.debug(
                "translation_completed sequence=%d french=%r english=%r",
                segment.sequence_number,
                segment.french,
                translation,
            )

    return translated_segments
