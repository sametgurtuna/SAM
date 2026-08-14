# SAM — Fact Extractor
# Extracts persistent personal facts (name, job, field of study, etc.)
# from conversational utterances. Lightweight, regex-based, zero extra LLM latency.

import logging
import re

logger = logging.getLogger(__name__)

# Each pattern: (regex, category, key). The first capture group is the value.
_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # Name
    (re.compile(r"\b(?:benim )?ad[ıi]m (\w+)", re.IGNORECASE), "identity", "name"),
    (re.compile(r"\bismim (\w+)", re.IGNORECASE), "identity", "name"),
    (re.compile(r"\bmy name is (\w+)", re.IGNORECASE), "identity", "name"),
    (re.compile(r"\bi'?m (\w+),? (?:and|nice)", re.IGNORECASE), "identity", "name"),

    # Profession / Job
    (re.compile(r"\b([\wçğıöşü]+(?:\s+[\wçğıöşü]+)?) olarak çalışıyorum", re.IGNORECASE),
     "profession", "job"),
    (re.compile(r"\bben bir ([\wçğıöşü]+(?:\s+[\wçğıöşü]+)?)[ıiuü]m\b", re.IGNORECASE),
     "profession", "job"),
    (re.compile(r"\bi work as an? ([\w\s]+?)(?:[.,!?]|$)", re.IGNORECASE),
     "profession", "job"),
    (re.compile(r"\bi'?m an? ([\w\s]+?) by profession", re.IGNORECASE),
     "profession", "job"),

    # Education / Field
    (re.compile(r"\b([\wçğıöşü]+(?:\s+[\wçğıöşü]+)?) bölümünü? okuyorum", re.IGNORECASE),
     "education", "field"),
    (re.compile(r"\bi(?:'m| am) studying ([\w\s]+?)(?:[.,!?]|$)", re.IGNORECASE),
     "education", "field"),
    (re.compile(r"\bi study ([\w\s]+?)(?:[.,!?]|$)", re.IGNORECASE),
     "education", "field"),
]


def extract_facts(text: str) -> list[tuple[str, str, str]]:
    """
    Extract (category, key, value) tuples from text.

    Args:
        text: Transcribed user utterance.

    Returns:
        List of extracted fact tuples (may be empty).
    """
    if not text or not text.strip():
        return []

    # Keep first match per (category, key) to avoid duplication
    seen: set[tuple[str, str]] = set()
    facts: list[tuple[str, str, str]] = []
    for pattern, category, key in _PATTERNS:
        if (category, key) in seen:
            continue
        match = pattern.search(text)
        if not match:
            continue
        value = match.group(1).strip().strip(".,!?")
        if not value or len(value) > 60:
            continue
        facts.append((category, key, value))
        seen.add((category, key))
        logger.debug("Fact extracted: [%s] %s = %s", category, key, value)

    return facts
