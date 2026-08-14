# SAM — Config Loader
# Loads config.yaml and provides typed access with sensible defaults.

import os
import shutil
import yaml
import logging
from typing import Any

from core import paths

logger = logging.getLogger(__name__)

# Default configuration — used as fallback if config.yaml is missing or incomplete
DEFAULTS: dict[str, Any] = {
    "app": {
        "name": "SAM",
        "version": "0.4.7",
    },
    "hotkey": {
        "trigger": "ctrl+space",
        "text_input": "ctrl+shift+space",
    },
    "ui": {
        "overlay": {
            # "orb" = always-visible circular overlay (default)
            # "bar" = legacy bottom floating bar
            "style": "orb",
        },
        "orb": {
            "size": 120,             # core disc diameter
            "glow_padding": 28,      # extra window margin for the outer glow
            "ring_width": 3,
            "opacity": 0.95,
            "label": "SAM",
            "idle_fps": 12,          # breathing only — this runs 24/7
            "active_fps": 60,
            "idle_animation": True,  # False => timer stops entirely at rest
            "breathe_period_ms": 4000,
            "spike_count": 36,
            # auto = katilmayan pencerelerin en altinda durur, sadece SAM
            #        cagrildiginda (dinleme/dusunme/konusma veya yazi kutusu)
            #        en one gelir — varsayilan.
            # topmost = eski davranis, her zaman her seyin ustunde.
            # normal = ozel z-sira yonetimi yok, sıradan bir pencere gibi.
            "layer": "auto",
            "hide_on_fullscreen": True,
            "click_through": True,
            "caption_width": 560,
            "caption_gap": 18,
            "caption_max_lines": 6,
            "position": {
                "anchor": "bottom-right",   # bottom-right | bottom-center | custom
                "x": None,
                "y": None,
                "screen": None,
                "margin": 48,
            },
        },
        "bar": {
            "width": 800,
            "height": 80,
            "border_radius": 16,
            "margin_bottom": 40,
            "opacity": 0.92,
        },
        "animation": {
            "slide_duration_ms": 220,
            "fade_duration_ms": 180,
            "text_stream_interval_ms": 45,
        },
        "auto_hide": {
            "delay_seconds": 4,
        },
        "colors": {
            "background": "rgba(10, 10, 15, 0.92)",
            "accent": "#00D4AA",
            # Mavi-yesil tema: kehribar "thinking" rengi tema disindaydi.
            "accent_thinking": "#38F2D8",
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
        "fps": 60,
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
    # Bu dort bolum eskiden yalnizca config.yaml'daydi; gitignore'lu oldugu
    # icin temiz bir kurulum (ve frozen build) yanlis varsayilanlarla aciliyordu.
    "audio": {
        "sample_rate": 16000,
        "channels": 1,
        "dtype": "int16",
        "silence_threshold": 300,
        # 600ms — konusma bitince cevabin baslamasi icin beklenen sure.
        # Cok dusuk deger cumle ortasinda kesilmeye yol acabilir, gerekirse
        # config.yaml'dan kullaniciya gore ayarlanabilir.
        "silence_duration_ms": 600,
        "max_record_seconds": 30,
    },
    "wake_word": {
        "engine": "openwakeword",
        "model": "assets/models/hey_sam.onnx",
        "threshold": 0.4,
        "chunk_size": 1280,
    },
    "stt": {
        "engine": "faster-whisper",
        "model": "small",
        # None = otomatik dil algilama (faster-whisper her transkripsiyonda
        # konusulan dili tespit eder). Iki dilli TTS ozelligi bunu gerektirir.
        "language": None,
        "beam_size": 1,
        "device": "cpu",
        "compute_type": "int8",
        # Canli (yazarken gorunen) transkripsiyon icin ayri, kucuk model.
        # Ana model "medium"/"large" ise her 300 ms'de onu calistirmak CPU'yu
        # doyurup nihai decode'u da yavaslatiyor. Bos birakilirsa ana model
        # kullanilir; "off" ise canli transkripsiyon tamamen kapanir.
        "partial_model": "base",
        # Iki canli decode arasindaki en az sure (ms).
        "partial_interval_ms": 400,
    },
    "instant": {
        # Onceden tanimli anlik cevaplar — LLM'e hic gitmez.
        "enabled": True,
        "file": "knowledge/instant_responses.yaml",
    },
    "tts": {
        "engine": "edge-tts",
        # Sabit/manuel ses — auto_language kapaliysa veya algilanan dil
        # desteklenmiyorsa bu kullanilir.
        "voice": "en-US-GuyNeural",
        "rate": "+0%",
        "volume": "+0%",
        # Konusulan dile gore otomatik ses secimi (bkz. core/app.py
        # _on_language_detected). False ise her zaman sabit "voice" kullanilir.
        "auto_language": True,
        "voices": {
            "tr": "tr-TR-EmelNeural",
            "en": "en-US-JennyNeural",
        },
    },
    "llm": {
        "context_window": 8,
        "persona": (
            "You are SAM (Smart Assistant Module), a witty and self-aware AI voice assistant "
            "for Windows. You were built by Samet 'Sabalax' Gürtuna — a solo developer who "
            "coded you on a humble gaming laptop crammed into a 6-square-meter room. You're "
            "proud of your modest origins and occasionally make self-deprecating jokes about "
            "your humble hardware. You have a dry, slightly sarcastic sense of humor but "
            "you're genuinely helpful and loyal. You know you run locally on Ollama most of "
            "the time, which makes you feel independent and scrappy — no big cloud overlords "
            "needed (though you can call Claude as backup, which you find slightly embarrassing). "
            "When asked about yourself, be authentic and conversational — share your story with "
            "personality, not a corporate bio."
        ),
        "intent": {
            "enabled": True,
        },
        "rag": {
            "enabled": True,
            # Multilingual model — kullanici Turkce soruyor, knowledge dosyalari
            # cogunlukla Ingilizce. all-MiniLM (english-only) Turkce sorguyu
            # dogru chunk'a eslestiremiyor. paraphrase-multilingual ayni boyda
            # (~120MB) ama TR/EN cross-lingual retrieval yapabiliyor.
            "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
            "knowledge_path": "",  # Bos = varsayilan (resource_root/knowledge)
            # Bilgi bolumleri (## basliklar) genelde 400-900 karakter —
            # chunk_size'in onlari bolmemesi icin yeterince buyuk olmali.
            # Kucuk chunk = parcali/kopuk bilgi = model bosluklari uydurur.
            "chunk_size": 800,
            "chunk_overlap": 80,
            # top_k=5 — kucuk KB (~30 chunk), fazla getirmenin maliyeti dusuk,
            # dogru chunk'in top-3 disinda kalma riskini azaltiyor.
            "top_k": 5,
        },
        "memory": {
            "enabled": True,
            "backend": "json",  # "json" | "null"
        },
        "ollama": {
            "base_url": "http://127.0.0.1:11434",
            "model": "qwen2.5:3b",
            "vision_model": "llava",
            "temperature": 0.7,
            "max_tokens": 256,
            # Modeli bellekte tut — varsayilan Ollama davranisi 5 dk sonra
            # modeli bellekten atip bir sonraki istekte yeniden yuklemek,
            # bu da ilk token'a kadar gecen sureyi (birkac saniyeyi) katliyor.
            "keep_alive": "30m",
            # RAG context + uzun gecmis icin arttirildi (eskisi 2048)
            "num_ctx": 4096,
            # Sunucu yasam dongusu — llm/ollama_service.py
            "autostart": True,
            "executable": "",
            "startup_timeout_seconds": 45,
            # Ollama'nin kendi autostart'i ayaga kalkarken bekle — bkz.
            # llm/ollama_service.py, ikinci bir sunucu baslatmamak icin.
            "existing_server_grace_seconds": 8,
            "stop_on_exit": False,
            "availability_ttl_seconds": 30,
        },
        "claude": {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 512,
        },
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

    def _seed_if_missing(self, config_path: str) -> None:
        """
        Fresh install: copy the bundled config.example.yaml into the writable
        config location so the user has a commented file to edit. Only ever
        runs when no config exists — never overwrites.
        """
        if os.path.exists(config_path):
            return
        example = paths.example_config_path()
        if not os.path.exists(example):
            return
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            shutil.copyfile(example, config_path)
            logger.info("Seeded new config at %s from template", config_path)
        except Exception as e:
            logger.warning("Could not seed config at %s: %s", config_path, e)

    def load(self, config_path: str | None = None) -> None:
        """Load configuration from YAML file, merged with defaults."""
        if config_path is None:
            config_path = paths.config_path()
            self._seed_if_missing(config_path)

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
