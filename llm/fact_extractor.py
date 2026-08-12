# SAM — Fact Extractor
# Kullanicinin konusmasindan kalici kisisel bilgi (isim, meslek, okudugu
# bolum vb.) cikarir. Regex-first, hafif — ek bir LLM cagrisi YAPMAZ, boylece
# yanit hizini etkilemez. Kapsam sinirli oldugu bilinen bir tercih —
# yetersiz kalirsa ileride LLM-tabanli cikarim eklenebilir.

import logging
import re

logger = logging.getLogger(__name__)

# Her kalip: (regex, category, key). Regex'in ilk grubu deger olarak alinir.
# Turkce ve Ingilizce en yaygin kaliplar — kucuk ve pragmatik tutuluyor.
_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # İsim
    (re.compile(r"\b(?:benim )?ad[ıi]m (\w+)", re.IGNORECASE), "identity", "name"),
    (re.compile(r"\bismim (\w+)", re.IGNORECASE), "identity", "name"),
    (re.compile(r"\bmy name is (\w+)", re.IGNORECASE), "identity", "name"),
    (re.compile(r"\bi'?m (\w+),? (?:and|nice)", re.IGNORECASE), "identity", "name"),

    # Meslek
    (re.compile(r"\b([\wçğıöşü]+(?:\s+[\wçğıöşü]+)?) olarak çalışıyorum", re.IGNORECASE),
     "profession", "job"),
    (re.compile(r"\bben bir ([\wçğıöşü]+(?:\s+[\wçğıöşü]+)?)[ıiuü]m\b", re.IGNORECASE),
     "profession", "job"),
    (re.compile(r"\bi work as an? ([\w\s]+?)(?:[.,!?]|$)", re.IGNORECASE),
     "profession", "job"),
    (re.compile(r"\bi'?m an? ([\w\s]+?) by profession", re.IGNORECASE),
     "profession", "job"),

    # Eğitim / okuduğu bölüm
    (re.compile(r"\b([\wçğıöşü]+(?:\s+[\wçğıöşü]+)?) bölümünü? okuyorum", re.IGNORECASE),
     "education", "field"),
    (re.compile(r"\bi(?:'m| am) studying ([\w\s]+?)(?:[.,!?]|$)", re.IGNORECASE),
     "education", "field"),
    (re.compile(r"\bi study ([\w\s]+?)(?:[.,!?]|$)", re.IGNORECASE),
     "education", "field"),
]


def extract_facts(text: str) -> list[tuple[str, str, str]]:
    """
    Metinden (category, key, value) uclulerini cikar.

    Args:
        text: Kullanicinin transkript edilmis cumlesi.

    Returns:
        Bulunan bilgi ucluleri — bos liste olabilir.
    """
    if not text or not text.strip():
        return []

    # Ayni (category, key) icin ilk eslesmeyi tut — birden fazla kalip ayni
    # cumlede tetiklenirse (ör. TR ve EN varyantlari) tekrar/celiski olmasin.
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
