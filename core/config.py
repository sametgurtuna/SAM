# SAM — Config Loader
# Loads config.yaml and provides typed access with sensible defaults.

import os
import yaml
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default configuration — used as fallback if config.yaml is missing or incomplete
DEFAULTS: dict[str, Any] = {
    "app": {
        "name": "SAM",
        "version": "0.1.0",
    },
    "hotkey": {
        "trigger": "ctrl+space",
    },
    "ui": {
        "bar": {
            "width": 800,
            "height": 80,
            "border_radius": 16,
            "margin_bottom": 40,
            "opacity": 0.92,
        },
        "animation": {
            "slide_duration_ms": 350,
            "fade_duration_ms": 250,
            "text_stream_interval_ms": 45,
        },
        "auto_hide": {
            "delay_seconds": 4,
        },
        "colors": {
            "background": "rgba(10, 10, 15, 0.92)",
            "accent": "#00D4AA",
            "accent_thinking": "#FFB84D",
            "accent_speaking": "#00D4AA",
            "accent_listening": "#00BFFF",
            "text_primary": "#E8E8E8",
            "text_secondary": "#888888",
            "border": "rgba(0, 212, 170, 0.15)",
        },
        "fonts": {
            "primary": "Segoe UI",
            "monospace": "Cascadia Code",
            "fallback": "Consolas",
            "size_transcript": 15,
            "size_status": 11,
        },
    },
    "waveform": {
        "bar_count": 35,
        "fps": 30,
        "min_height": 3,
        "max_height": 32,
        "bar_width": 3,
        "bar_gap": 2,
        "color": "#00D4AA",
    },
    "mock": {
        "listening_duration_ms": 2500,
        "thinking_duration_ms": 1200,
        "user_transcript": "What's the weather like today?",
        "assistant_response": "It's 24°C and sunny in Istanbul right now. Perfect day to go outside.",
    },
    "logging": {
        "level": "DEBUG",
        "file": "logs/sam.log",
    },
    "tts": {
        "engine": "edge-tts",
        "voice": "en-US-GuyNeural",
        "rate": "+0%",
        "volume": "+0%",
    },
    "spotify": {
        "client_id": "",
        "client_secret": "",
        "redirect_uri": "http://localhost:8080",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override dict into base dict. Override wins on conflicts."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class Config:
    """Singleton configuration manager for SAM."""

    _instance: "Config | None" = None
    _data: dict[str, Any]
    _config_path: str | None

    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = {}
            cls._instance._config_path = None
        return cls._instance

    def load(self, config_path: str | None = None) -> None:
        """Load configuration from YAML file, merged with defaults."""
        if config_path is None:
            # Look for config.yaml relative to project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(project_root, "config.yaml")

        self._config_path = config_path

        file_config: dict[str, Any] = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    file_config = yaml.safe_load(f) or {}
                logger.info("Loaded config from %s", config_path)
            except Exception as e:
                logger.warning("Failed to load config from %s: %s", config_path, e)
        else:
            logger.warning("Config file not found at %s, using defaults", config_path)

        self._data = _deep_merge(DEFAULTS, file_config)

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Get a nested config value using dot-path keys.
        
        Usage:
            config.get("ui", "bar", "width")           → 800
            config.get("ui", "colors", "accent")       → "#00D4AA"
            config.get("nonexistent", default="fallback") → "fallback"
        """
        current = self._data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def set(self, *keys: str, value: Any) -> None:
        """
        Set a nested config value.

        Usage:
            config.set("stt", "model", value="base")
            config.set("llm", "ollama", "temperature", value=0.5)
        """
        if not keys:
            return

        current = self._data
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def save(self) -> bool:
        """
        Write current config data back to config.yaml.
        Returns True on success, False on failure.
        """
        if self._config_path is None:
            logger.error("Cannot save — config path not set (load() not called)")
            return False

        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self._data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                    width=120,
                )
            logger.info("Config saved to %s", self._config_path)
            return True
        except Exception as e:
            logger.error("Failed to save config to %s: %s", self._config_path, e)
            return False

    @property
    def data(self) -> dict[str, Any]:
        """Raw config dictionary access."""
        return self._data


# Module-level convenience instance
config = Config()
