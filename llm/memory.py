# SAM — Long-Term Memory Interface
# Uzun vadeli kullanici hafizasi icin arayuz ve implementasyonlar.
# Varsayilan backend JsonMemory (llm.memory.enabled=true) — kullanici
# konustukca ogrenilen bilgiler (isim, meslek, okul vb.) kalici olarak
# saklanir ve her turn'un system prompt'una kisa bir ozet olarak eklenir.
# llm.memory.enabled=false ise NullMemory (no-op) kullanilir.

import json
import logging
import os
import time
from abc import ABC, abstractmethod

from core import paths

logger = logging.getLogger(__name__)


class MemoryStore(ABC):
    """Uzun vadeli kullanici hafizasi arayuzu."""

    @abstractmethod
    def store(self, key: str, value: str, category: str = "general") -> None:
        """Bir bilgiyi kaydet."""

    @abstractmethod
    def retrieve(self, query: str, limit: int = 5) -> list[str]:
        """Sorguya uyan bilgileri getir."""

    @abstractmethod
    def get_context_summary(self) -> str | None:
        """Prompt'a eklenecek hafiza ozeti. None = ekleme."""


class NullMemory(MemoryStore):
    """Hafiza devre disi — tum islemler no-op."""

    def store(self, key: str, value: str, category: str = "general") -> None:
        pass

    def retrieve(self, query: str, limit: int = 5) -> list[str]:
        return []

    def get_context_summary(self) -> str | None:
        return None


# Prompt'a eklenecek ozette en fazla kac fact yer alsin — hepsini eklemek
# her turn'un system prompt'unu gereksiz sisirir.
_MAX_SUMMARY_FACTS = 12


class JsonMemory(MemoryStore):
    """
    Minimal JSON tabanli hafiza.

    user_data_dir()/memory.json'da saklar (tek gercek kaynak — okuma buradan
    yapilir). Ayrica ayni klasore, kullanicinin gorup duzenleyebilecegi bir
    memory.md aynasi da yazilir (bkz. _export_markdown).
    Basit keyword eslestirme — semantik arama yok.
    Gelecekte embedding-tabanli arama ile degistirilebilir.
    """

    def __init__(self) -> None:
        self._path = os.path.join(paths.user_data_dir(), "memory.json")
        self._md_path = os.path.join(paths.user_data_dir(), "memory.md")
        self._data: dict[str, dict[str, dict]] = self._load()

    def _load(self) -> dict:
        if os.path.exists(self._path):
            try:
                with open(self._path, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Memory file corrupt, starting fresh: %s", e)
        return {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.error("Failed to save memory: %s", e)
        self._export_markdown()

    def _export_markdown(self) -> None:
        """
        Kullanicinin okuyup duzenleyebilecegi insan-okunur bir kopya yaz.
        JSON tek gercek kaynak kalir — bu sadece bir gorunum/aynadir,
        knowledge/*.md dosyalarindaki konvansiyonu takip eder.
        """
        lines = ["# SAM — Kullanici Hafizasi\n"]
        for category in sorted(self._data.keys()):
            entries = self._data[category]
            if not entries:
                continue
            lines.append(f"## {category}\n")
            for key, entry in sorted(entries.items()):
                lines.append(f"- **{key}**: {entry.get('value', '')}")
            lines.append("")

        try:
            with open(self._md_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except OSError as e:
            logger.error("Failed to export memory.md: %s", e)

    def store(self, key: str, value: str, category: str = "general") -> None:
        if category not in self._data:
            self._data[category] = {}
        self._data[category][key] = {
            "value": value,
            "timestamp": time.time(),
        }
        self._save()
        logger.debug("Memory stored: [%s] %s", category, key)

    def retrieve(self, query: str, limit: int = 5) -> list[str]:
        query_lower = query.lower()
        results: list[str] = []
        for cat_data in self._data.values():
            for key, entry in cat_data.items():
                if (query_lower in key.lower()
                        or query_lower in entry["value"].lower()):
                    results.append(entry["value"])
                    if len(results) >= limit:
                        return results
        return results

    def get_context_summary(self) -> str | None:
        # En son N fact'i (timestamp'e gore) ozet olarak dondur.
        flat: list[tuple[float, str, str, str]] = []
        for category, entries in self._data.items():
            for key, entry in entries.items():
                flat.append((
                    entry.get("timestamp", 0),
                    category,
                    key,
                    entry.get("value", ""),
                ))

        if not flat:
            return None

        flat.sort(key=lambda t: t[0], reverse=True)
        top = flat[:_MAX_SUMMARY_FACTS]
        return "\n".join(f"- [{cat}] {key}: {value}" for _, cat, key, value in top)


def create_memory_store() -> MemoryStore:
    """Config'e gore uygun hafiza backend'ini olustur."""
    from core.config import config

    enabled = config.get("llm", "memory", "enabled", default=False)
    if not enabled:
        return NullMemory()

    backend = config.get("llm", "memory", "backend", default="json")
    if backend == "json":
        logger.info("Long-term memory enabled (JSON backend)")
        return JsonMemory()

    logger.warning("Unknown memory backend '%s', using NullMemory", backend)
    return NullMemory()
