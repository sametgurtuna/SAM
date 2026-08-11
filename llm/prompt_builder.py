# SAM — Per-Turn Prompt Builder
# System prompt'u her turn icin dinamik olarak olusturur.
# Katmanli yapi: persona + rules + mode + memory + knowledge

import logging

from core.config import config
from llm.modes import MODES

logger = logging.getLogger(__name__)

# Davranis kurallari — her zaman eklenir, moddan bagimsiz.
BEHAVIOR_RULES = """Rules:
- Give short, direct answers (1-3 sentences) unless asked to elaborate
- Be conversational but efficient — no filler, no fluff
- If asked to do something on the computer, confirm what you'll do
- You can understand commands like opening apps, controlling volume, etc.
- Respond naturally as if speaking — your response will be read aloud via TTS
- If asked to write code, put it inside markdown code blocks (```language ... ```) and do not explain the code line by line
- For everything else, don't use markdown, bullet points, or formatting — plain spoken text only
- If you don't know something, say so briefly"""

# Config'te persona yoksa kullanilacak fallback
_DEFAULT_PERSONA = (
    "You are SAM, a fast and helpful desktop voice assistant."
)


class PromptBuilder:
    """
    Turn bazinda system prompt olusturur.

    Katmanlar (sirasıyla):
      1. BASE PERSONA   — config'ten, ~100 kelime
      2. BEHAVIOR RULES  — sabit, her zaman
      3. MODE            — dinamik, sadece aktifse (ör. FENERBAHCE)
      4. USER MEMORY     — gelecek, su an bos
      5. RETRIEVED KNOWLEDGE — RAG sonucu, varsa

    config.yaml'da "system_prompt" tanimliysa tum katmanlar atlanir
    ve o metin birebir kullanilir (geriye uyumluluk).
    """

    def __init__(self) -> None:
        # Geriye uyumluluk: tam override
        self._custom_prompt: str | None = config.get(
            "llm", "system_prompt", default=None
        )

        # Persona — config'ten veya varsayilan
        self._persona: str = config.get(
            "llm", "persona", default=_DEFAULT_PERSONA
        )

    def build(
        self,
        mode: str | None = None,
        knowledge: str | None = None,
        memory: str | None = None,
    ) -> str:
        """
        Bu turn icin tam system prompt'u olustur.

        Args:
            mode: Aktif mod ismi ("FENERBAHCE", vb.) veya None.
            knowledge: RAG'den alinan bilgi metni veya None.
            memory: Uzun vadeli hafizadan alinan ozet veya None.

        Returns:
            Birlestirilmis system prompt.
        """
        # Tam override varsa direkt dondur
        if self._custom_prompt:
            return self._custom_prompt

        parts: list[str] = [self._persona, BEHAVIOR_RULES]

        # Mod talimatlari
        if mode and mode in MODES:
            parts.append(MODES[mode].instructions)

        # Kullanici hafizasi (gelecek icin hazir)
        if memory:
            parts.append(f"User context:\n{memory}")

        # RAG bilgisi
        if knowledge:
            parts.append(f"Relevant knowledge:\n{knowledge}")

        prompt = "\n\n".join(parts)
        logger.debug(
            "System prompt built: %d chars, mode=%s, has_knowledge=%s",
            len(prompt), mode or "NORMAL", bool(knowledge),
        )
        return prompt
