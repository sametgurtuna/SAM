# SAM — Long-Term Memory Interface
# Uzun vadeli kullanici hafizasi icin arayuz ve minimal implementasyon.
# Su an devre disi (NullMemory) — gelecekte JsonMemory veya embedding-tabanli
# bir implementasyon aktif edilebilir.

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


class JsonMemory(MemoryStore):
    """
    Minimal JSON tabanli hafiza.

    %LOCALAPPDATA%/SAM/memory.json'da saklar.
    Basit keyword eslestirme — semantik arama yok.
    Gelecekte embedding-tabanli arama ile degistirilebilir.
    """

    def __init__(self) -> None:
        self._path = os.path.join(paths.user_data_dir(), "memory.json")
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
        # Gelecekte en son N fact'i ozet olarak dondur
        return None


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
