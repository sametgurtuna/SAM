# SAM — Instant Responder
# Onceden tanimli soru/cevap eslestirmesi. Siri'nin "hazir cevaplari" gibi:
# eslesme bulunursa STT ciktisi hicbir zaman LLM'e gitmez, cevap dogrudan
# TTS'e verilir (~0 ms). Eslesme yoksa CommandRouter → LLM zinciri devam eder.
#
# Veri dosyasi: knowledge/instant_responses.yaml (kullanici duzenleyebilir).

import logging
import os
import random
import re
import shutil
from datetime import datetime
from typing import Any

import yaml

from core import paths

logger = logging.getLogger(__name__)

# Turkce karakter katlama — "saat kac" ve "saat kaç" ayni anahtara dusmeli.
_FOLD = str.maketrans("çğıöşüâîû", "cgiosuaiu")

_PUNCT_RE = re.compile(r"[.,!?;:'\"`´’]+")
_WS_RE = re.compile(r"\s+")
# Hitap ve nezaket dolgulari — router._clean_text ile ayni mantik.
_LEAD_RE = re.compile(
    r"^(?:hey\s+sam|hey\s+samet|sam|samet|please|lütfen|lutfen|ya|hey)\s+",
    re.IGNORECASE,
)
_TRAIL_RE = re.compile(r"\s+(?:please|lütfen|lutfen|sam|samet)$", re.IGNORECASE)

_TR_DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
_TR_MONTHS = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]

DEFAULT_FILE = os.path.join("knowledge", "instant_responses.yaml")


def normalize(text: str) -> str:
    """Eslestirme anahtari uret: kucuk harf, noktalamasiz, aksansiz, dolgusuz."""
    text = text.strip().lower()
    text = _PUNCT_RE.sub("", text)
    text = _WS_RE.sub(" ", text).strip()
    text = _LEAD_RE.sub("", text)
    text = _TRAIL_RE.sub("", text)
    return text.translate(_FOLD).strip()


class InstantResponder:
    """
    Sabit ifadeler icin O(1) sozluk aramasi.

    YAML formati:

        responses:
          - patterns: ["merhaba", "selam", "hello"]
            response: ["Merhaba!", "Selam, buradayım."]
          - patterns: ["saat kac"]
            response: "Saat {time}."
            lang: tr
          - patterns: ["tesekkurler"]
            response: "Rica ederim."
            match: contains

    `match: exact` (varsayilan) sozluk aramasidir — bedava. `match: contains`
    girdileri sirayla taranir, bu yuzden az sayida tutulmali.
    Cevap metninde {time}, {date}, {day} yer tutuculari desteklenir.
    """

    def __init__(self, file_path: str | None = None) -> None:
        self._exact: dict[str, dict[str, Any]] = {}
        self._contains: list[tuple[str, dict[str, Any]]] = []
        self._path = self._resolve_path(file_path or DEFAULT_FILE)
        self._load()

    # ─── Dosya konumu ─────────────────────────────────────────────

    @staticmethod
    def _resolve_path(rel: str) -> str:
        """
        Kullanicinin duzenleyebilecegi kopyanin yolunu dondur.

        Kurulu (frozen) surumde paketteki kopya Program Files altinda ve salt
        okunur — bu yuzden config.yaml'da oldugu gibi, ilk acilista yazilabilir
        veri klasorune (%APPDATA%\\SAM) kopyalanir. Kullanici oradaki dosyayi
        duzenler; paketteki kopya yalnizca sablon olarak kalir.
        """
        if os.path.isabs(rel):
            return rel

        user_copy = os.path.join(paths.user_data_dir(), rel)
        if os.path.exists(user_copy):
            return user_copy

        bundled = paths.resource_path(rel)
        if not os.path.exists(bundled):
            return user_copy  # ikisi de yok — _load uyarip bos gececek

        # Kaynak ile hedef ayni dosyaysa (kaynaktan calisirken oyle)
        # kopyalanacak bir sey yok.
        if os.path.normcase(os.path.abspath(bundled)) == os.path.normcase(
            os.path.abspath(user_copy)
        ):
            return bundled

        try:
            os.makedirs(os.path.dirname(user_copy), exist_ok=True)
            shutil.copyfile(bundled, user_copy)
            logger.info("Seeded editable instant responses at %s", user_copy)
            return user_copy
        except Exception as e:
            logger.warning("Could not seed instant responses at %s: %s", user_copy, e)
            return bundled

    @property
    def path(self) -> str:
        """Okunan (ve kullanicinin duzenleyebilecegi) dosyanin tam yolu."""
        return self._path

    # ─── Yukleme ──────────────────────────────────────────────────

    def _load(self) -> None:
        if not os.path.exists(self._path):
            logger.warning("Instant responses file not found: %s", self._path)
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error("Failed to load instant responses (%s): %s", self._path, e)
            return

        for entry in data.get("responses") or []:
            patterns = entry.get("patterns") or []
            response = entry.get("response")
            if not patterns or not response:
                continue
            meta = {
                "response": response,
                "lang": entry.get("lang", "en"),
            }
            mode = (entry.get("match") or "exact").lower()
            for pattern in patterns:
                key = normalize(str(pattern))
                if not key:
                    continue
                if mode == "contains":
                    self._contains.append((key, meta))
                else:
                    self._exact[key] = meta

        logger.info("Instant responses loaded: %d exact, %d contains (%s)",
                    len(self._exact), len(self._contains), self._path)

    def reload(self) -> None:
        """Veri dosyasini yeniden oku (ayarlar penceresinden cagrilabilir)."""
        self._exact.clear()
        self._contains.clear()
        self._load()

    @property
    def count(self) -> int:
        return len(self._exact) + len(self._contains)

    # ─── Eslestirme ───────────────────────────────────────────────

    def match(self, transcript: str) -> tuple[str, str] | None:
        """
        (cevap, dil_kodu) dondur, eslesme yoksa None. Mikrosaniyeler surer.
        """
        if not self._exact and not self._contains:
            return None

        key = normalize(transcript)
        if not key:
            return None

        meta = self._exact.get(key)
        if meta is None:
            for needle, candidate in self._contains:
                if needle in key:
                    meta = candidate
                    break
        if meta is None:
            return None

        response = meta["response"]
        if isinstance(response, (list, tuple)):
            response = random.choice(list(response))
        lang = meta.get("lang", "en")
        return self._fill(str(response), lang), lang

    # ─── Yer tutucular ────────────────────────────────────────────

    @staticmethod
    def _fill(text: str, lang: str) -> str:
        if "{" not in text:
            return text
        now = datetime.now()
        if lang == "tr":
            day = _TR_DAYS[now.weekday()]
            date = f"{now.day} {_TR_MONTHS[now.month - 1]} {now.year}"
            time_str = f"{now.hour:02d}:{now.minute:02d}"
        else:
            day = now.strftime("%A")
            date = now.strftime("%B %d, %Y")
            time_str = now.strftime("%I:%M %p").lstrip("0")
        return (text.replace("{time}", time_str)
                    .replace("{date}", date)
                    .replace("{day}", day))
