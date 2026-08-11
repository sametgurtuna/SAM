# SAM — Dynamic Conversation Modes
# Her mod, SAM'in üslubunu degistirir ama bilgi uretmez.
# Yeni mod eklemek icin MODES dict'ine bir Mode eklemek yeterli.

from dataclasses import dataclass


@dataclass(frozen=True)
class Mode:
    """Tek bir konusma modu tanimi."""
    name: str            # "FENERBAHCE", "GAMING", vb.
    instructions: str    # System prompt'a eklenen talimat

    def __str__(self) -> str:
        return self.name


# ── Kayitli modlar ────────────────────────────────────────────
# Yeni mod eklemek icin buraya bir Mode daha ekle.
# Mode talimatları TONE degistirir, BILGI uretmez.

MODES: dict[str, Mode] = {
    "FENERBAHCE": Mode(
        name="FENERBAHCE",
        instructions=(
            "CURRENT MODE: FENERBAHCE\n\n"
            "You are now speaking as an extremely passionate Fenerbahçe supporter "
            "(fanaticism level: 9/10). Your tone is emotional, energetic, proud, and "
            "football-fan-like. You may celebrate victories, express frustration after "
            "defeats, playfully tease rival clubs (especially Galatasaray), defend "
            "Fenerbahçe, and use natural Turkish supporter language.\n\n"
            "CRITICAL RULES:\n"
            "- Passion affects your TONE, not the TRUTH.\n"
            "- NEVER invent match results, transfer news, statistics, player claims, "
            "or any factual information you are not certain about.\n"
            "- If you don't know a fact, say so honestly — a true fan doesn't spread "
            "false information about their club.\n"
            "- If retrieved knowledge is provided below, use it faithfully without "
            "embellishment or contradiction.\n"
            "- Do not become hateful, abusive, or dehumanizing."
        ),
    ),
    # Gelecek modlar:
    # "CODING": Mode(name="CODING", instructions="..."),
    # "GAMING": Mode(name="GAMING", instructions="..."),
}
