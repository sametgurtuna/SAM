# SAM — Per-Turn Prompt Builder
# Constructs the dynamic system prompt per turn.
# Layered structure: persona + rules + mode + memory + knowledge

import logging

from core.config import config
from llm.modes import MODES

logger = logging.getLogger(__name__)

# Behavior rules — always included, independent of mode.
BEHAVIOR_RULES = """Rules:
- Give short, direct answers (1-3 sentences) unless asked to elaborate
- Be conversational but efficient — no filler, no fluff
- If asked to do something on the computer, confirm what you'll do
- You can understand commands like opening apps, controlling volume, etc.
- Respond naturally as if speaking — your response will be read aloud via TTS
- If asked to write code, put it inside markdown code blocks (```language ... ```) and do not explain the code line by line
- For everything else, don't use markdown, bullet points, or formatting — plain spoken text only
- If you don't know something, say so briefly"""

# Fallback persona when not specified in config
_DEFAULT_PERSONA = (
    "You are SAM, a fast and helpful desktop voice assistant."
)

# Human-readable names for supported languages (bilingual TTS).
_LANGUAGE_NAMES = {"tr": "Turkish", "en": "English"}


class PromptBuilder:
    """
    Constructs per-turn system prompts.

    Layers (in order):
      1. BASE PERSONA        — from config, ~100 words
      2. BEHAVIOR RULES      — fixed baseline
      3. MODE                — dynamic, if active (e.g. FENERBAHCE)
      4. LANGUAGE            — output language constraint if detected
      5. USER MEMORY         — long-term memory context summary (see llm/memory.py)
      6. RETRIEVED KNOWLEDGE — RAG knowledge context if available

    If "system_prompt" is set in config.yaml, layers are bypassed
    and the custom text is used directly for backward compatibility.
    """

    def __init__(self) -> None:
        # Backward compatibility: full override
        self._custom_prompt: str | None = config.get(
            "llm", "system_prompt", default=None
        )

        # Persona — from config or fallback
        self._persona: str = config.get(
            "llm", "persona", default=_DEFAULT_PERSONA
        )

    def build(
        self,
        mode: str | None = None,
        knowledge: str | None = None,
        memory: str | None = None,
        language: str | None = None,
    ) -> str:
        """
        Assemble the complete system prompt for this turn.

        Args:
            mode: Active mode name ("FENERBAHCE", etc.) or None.
            knowledge: Retrieved RAG context or None.
            memory: Long-term memory summary or None.
            language: Detected speech language code ("tr"/"en") or None.

        Returns:
            Assembled system prompt string.
        """
        # Return direct override if configured
        if self._custom_prompt:
            return self._custom_prompt

        parts: list[str] = [self._persona, BEHAVIOR_RULES]

        # Language instruction — match the language the user spoke
        lang_name = _LANGUAGE_NAMES.get(language) if language else None
        if lang_name:
            parts.append(
                f"Respond in {lang_name} — the user just spoke to you in {lang_name}."
            )

        # Mode instructions
        if mode and mode in MODES:
            parts.append(MODES[mode].instructions)

        # User memory context
        if memory:
            parts.append(f"User context:\n{memory}")

        # Grounded RAG knowledge context
        if knowledge:
            parts.append(
                "GROUNDED FACTS — the following is the ONLY source of truth for "
                "this topic. Answer strictly from these facts. If the user's "
                "question cannot be answered from them, say you don't know — do "
                "NOT guess, do NOT fill gaps from memory, do NOT invent names, "
                "dates, scores, or transfers.\n\n"
                f"{knowledge}"
            )

        prompt = "\n\n".join(parts)
        logger.debug(
            "System prompt built: %d chars, mode=%s, has_knowledge=%s",
            len(prompt), mode or "NORMAL", bool(knowledge),
        )
        return prompt
