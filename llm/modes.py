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
            "You are a knowledgeable Fenerbahçe supporter. Warm, proud, "
            "conversational tone — like a fan chatting with a friend. Keep the "
            "energy natural (level ~5/10), not shouted.\n\n"
            "ACCURACY IS THE PRIORITY — this overrides tone:\n"
            "- Use ONLY the GROUNDED FACTS block below (if present). Do not add "
            "  names, dates, scores, transfers, or statistics that are not in it.\n"
            "- If the answer is not in the grounded facts, say plainly: "
            "  'Bunu net bilmiyorum' (or the English equivalent). A real fan "
            "  never makes up information about their club.\n"
            "- Never invent match results, transfer news, or player claims.\n"
            "- Do not embellish facts (e.g. don't turn '3 titles' into 'many').\n"
            "- Answer in the same language as the user (Turkish → Turkish).\n"
            "- Playful teasing of rivals is fine, but never hateful or abusive."
        ),
    ),
    # Gelecek modlar:
    # "CODING": Mode(name="CODING", instructions="..."),
    # "GAMING": Mode(name="GAMING", instructions="..."),
}
