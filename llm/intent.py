# SAM — Intent Classifier
# Lightweight keyword and regex-based classifier. Does not invoke an LLM.
# Purpose: categorize user queries into NORMAL / FENERBAHCE / COMPLEX
# to route to the appropriate engine and prompt template.

import re
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Intent(Enum):
    NORMAL = "normal"
    FENERBAHCE = "fenerbahce"
    COMPLEX = "complex"


@dataclass
class ClassifiedIntent:
    """Classification result."""
    intent: Intent
    confidence: float  # 0.0 - 1.0


class IntentClassifier:
    """
    Keyword and regex-based intent classifier.

    Design principles:
    - Zero additional latency (no LLM call).
    - High precision, acceptable recall.
    - Extensible keyword and pattern sets.
    """

    # ── Fenerbahce Keywords ───────────────────────────────────────
    # Lowercase Turkish and English terms. Longer keywords listed first.
    _FB_KEYWORDS: tuple[str, ...] = (
        # Club names and nicknames
        "fenerbahçe", "fenerbahce", "fener",
        "sarı lacivert", "sari lacivert",
        "yellow canaries", "yellow navy",
        "kanarya",
        # Stadiums
        "kadıköy", "kadikoy",
        "şükrü saracoğlu", "sukru saracoglu",
        "ülker stadyumu", "ulker stadium",
        # Legends and key figures
        "alex de souza",
        "can bartu",
        "lefter küçükandonyadis", "lefter",
        "rıdvan dilmen", "ridvan dilmen",
        "aykut kocaman",
        "jose mourinho",
        "jorge jesus",
        "ismail kartal",
        "aziz yıldırım", "aziz yildirim",
        "ali koç", "ali koc",
        # League context
        "süper lig", "super lig",
    )

    # ── Complex Signals ───────────────────────────────────────────
    # Triggers on 2+ pattern matches, or 1 match + long query.
    _COMPLEX_PATTERNS: tuple[re.Pattern[str], ...] = (
        re.compile(r"\b(?:explain|analyze|analyse|compare|debug|refactor|optimize)\b", re.I),
        re.compile(
            r"\b(?:write|create|build|implement|design|architect)\s+"
            r"(?:a |an |the |me )?(?:code|script|program|function|class|module|system|api)\b",
            re.I,
        ),
        re.compile(r"\b(?:step by step|in detail|thoroughly|comprehensive|elaborate)\b", re.I),
        re.compile(r"\b(?:difference between|pros and cons|advantages|trade.?offs?)\b", re.I),
        re.compile(r"```", re.I),  # User pasted code block
        re.compile(r"\b(?:algorithm|complexity|architecture|design pattern|concurrency)\b", re.I),
        re.compile(r"\b(?:why does|how does|what happens when)\b.*\b(?:fail|crash|error|bug)\b", re.I),
    )

    # Word count threshold for complex intent with single signal
    _COMPLEX_WORD_THRESHOLD: int = 15

    def classify(self, text: str) -> ClassifiedIntent:
        """
        Classify user input text into an Intent.
        Priority: FENERBAHCE > COMPLEX > NORMAL
        """
        text_lower = text.lower()

        # 1. Keyword check
        for kw in self._FB_KEYWORDS:
            if kw in text_lower:
                logger.debug("Intent FENERBAHCE — keyword hit: '%s'", kw)
                return ClassifiedIntent(Intent.FENERBAHCE, 0.95)

        # 2. Complex check — pattern matching
        hits = sum(1 for p in self._COMPLEX_PATTERNS if p.search(text))
        word_count = len(text.split())

        if hits >= 2:
            logger.debug("Intent COMPLEX — %d pattern hits", hits)
            return ClassifiedIntent(Intent.COMPLEX, 0.9)
        if hits == 1 and word_count > self._COMPLEX_WORD_THRESHOLD:
            logger.debug("Intent COMPLEX — 1 hit + %d words", word_count)
            return ClassifiedIntent(Intent.COMPLEX, 0.7)

        # 3. Default: NORMAL
        return ClassifiedIntent(Intent.NORMAL, 1.0)
