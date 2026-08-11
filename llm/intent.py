# SAM — Intent Classifier
# Hafif keyword/regex tabanli siniflandirici. LLM cagirmaz.
# Amac: her kullanici mesajini NORMAL / FENERBAHCE / COMPLEX olarak etiketle
# ve dogru motora (Qwen vs Claude) yonlendir.

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
    """Siniflandirma sonucu."""
    intent: Intent
    confidence: float  # 0.0 - 1.0


class IntentClassifier:
    """
    Keyword + regex tabanli intent siniflandirici.

    Tasarim kararlari:
    - LLM cagirmaz — sifir ek gecikme.
    - Yuksek precision, kabul edilebilir recall: yanlis pozitif kotu,
      yanlis negatif kabul edilebilir (normal cevap verir sadece).
    - Genisletilebilir: yeni keyword setleri veya regex pattern'leri ekle.
    """

    # ── Fenerbahce keyword'leri ──────────────────────────────────
    # Kucuk harf, Turkce ve Ingilizce. Uzun keyword'ler onde (greedier match).
    _FB_KEYWORDS: tuple[str, ...] = (
        # Kulup isimleri ve lakaplaR
        "fenerbahçe", "fenerbahce", "fener",
        "sarı lacivert", "sari lacivert",
        "yellow canaries", "yellow navy",
        "kanarya",
        # Stadyum
        "kadıköy", "kadikoy",
        "şükrü saracoğlu", "sukru saracoglu",
        "ülker stadyumu", "ulker stadium",
        # Efsaneler & onemli isimler
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
        # Lig & organizasyon (FB baglami gucluyse)
        "süper lig", "super lig",
    )

    # ── Complex sinyalleri ───────────────────────────────────────
    # Bunlarin 2+ tanesi eslesmeli, veya 1 tanesi + uzun sorgu.
    _COMPLEX_PATTERNS: tuple[re.Pattern[str], ...] = (
        re.compile(r"\b(?:explain|analyze|analyse|compare|debug|refactor|optimize)\b", re.I),
        re.compile(
            r"\b(?:write|create|build|implement|design|architect)\s+"
            r"(?:a |an |the |me )?(?:code|script|program|function|class|module|system|api)\b",
            re.I,
        ),
        re.compile(r"\b(?:step by step|in detail|thoroughly|comprehensive|elaborate)\b", re.I),
        re.compile(r"\b(?:difference between|pros and cons|advantages|trade.?offs?)\b", re.I),
        re.compile(r"```", re.I),  # Kullanici kod yapistirmis
        re.compile(r"\b(?:algorithm|complexity|architecture|design pattern|concurrency)\b", re.I),
        re.compile(r"\b(?:why does|how does|what happens when)\b.*\b(?:fail|crash|error|bug)\b", re.I),
    )

    # Complex icin minimum kelime sayisi (tek sinyal varsa)
    _COMPLEX_WORD_THRESHOLD: int = 15

    def classify(self, text: str) -> ClassifiedIntent:
        """
        Kullanici mesajini siniflandir.

        Oncelik: FENERBAHCE > COMPLEX > NORMAL
        """
        text_lower = text.lower()

        # 1. Fenerbahce kontrolu — keyword match
        for kw in self._FB_KEYWORDS:
            if kw in text_lower:
                logger.debug("Intent FENERBAHCE — keyword hit: '%s'", kw)
                return ClassifiedIntent(Intent.FENERBAHCE, 0.95)

        # 2. Complex kontrolu — pattern match
        hits = sum(1 for p in self._COMPLEX_PATTERNS if p.search(text))
        word_count = len(text.split())

        if hits >= 2:
            logger.debug("Intent COMPLEX — %d pattern hits", hits)
            return ClassifiedIntent(Intent.COMPLEX, 0.9)
        if hits == 1 and word_count > self._COMPLEX_WORD_THRESHOLD:
            logger.debug("Intent COMPLEX — 1 hit + %d words", word_count)
            return ClassifiedIntent(Intent.COMPLEX, 0.7)

        # 3. Varsayilan: NORMAL
        return ClassifiedIntent(Intent.NORMAL, 1.0)
