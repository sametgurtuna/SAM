# SAM — LLM Router
# Auto-detects the best available LLM engine and manages conversation context.
# Priority: Ollama (local, free) → Claude (cloud, paid) → None (error)

import logging
import threading
from collections import deque

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from core.config import config
from llm.base import LLMEngine
from llm.ollama_engine import OllamaEngine
from llm.claude_engine import ClaudeEngine

logger = logging.getLogger(__name__)

# SAM's system prompt — short, direct, no-fluff assistant personality
SYSTEM_PROMPT = """You are SAM, a fast and helpful desktop voice assistant. Rules:
- Give short, direct answers (1-3 sentences) unless asked to elaborate
- Be conversational but efficient — no filler, no fluff
- If asked to do something on the computer, confirm what you'll do
- You can understand commands like opening apps, controlling volume, etc.
- Respond naturally as if speaking — your response will be read aloud via TTS
- Don't use markdown, bullet points, or formatting — plain spoken text only
- If you don't know something, say so briefly"""


class LLMRouter(QObject):
    """
    Routes LLM requests to the best available engine.
    
    Manages:
        - Engine auto-detection (Ollama → Claude → None)
        - Rolling conversation context (last N exchanges)
        - System prompt injection
        - Signal forwarding from active engine
    
    Signals:
        token_received(str): Forwarded from active engine.
        generation_complete(str): Forwarded from active engine.
        generation_error(str): Forwarded or generated on routing failure.
        engine_status(str): Reports which engine is active.
    """

    token_received = pyqtSignal(str)
    generation_complete = pyqtSignal(str)
    generation_error = pyqtSignal(str)
    engine_status = pyqtSignal(str)

    # Internal: worker thread -> Qt main thread. Payload is an LLMEngine or None.
    _engine_detected = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()

        self._max_context: int = config.get("llm", "context_window", default=5)
        self._system_prompt: str = config.get("llm", "system_prompt", default=SYSTEM_PROMPT)

        # Conversation history — rolling deque of (role, content) pairs
        self._history: deque[dict[str, str]] = deque(maxlen=self._max_context * 2)

        # Available engines (tried in order)
        self._engines: list[LLMEngine] = [
            OllamaEngine(),
            ClaudeEngine(),
        ]
        self._active_engine: LLMEngine | None = None
        self._detecting: bool = False
        self._retry_pending: bool = False
        # Baglanti hatasi sonrasi tek sessiz tekrar icin saklanan istek
        self._pending_request: tuple[str, str | None] | None = None

        self._engine_detected.connect(self._on_engine_detected)

        # Motor tespiti her engine icin 2 sn timeout'lu bir HTTP istegi yapiyor.
        # Bunu __init__ icinde senkron calistirmak, Ollama kapaliyken acilisi
        # 2 sn blokluyordu. Event loop baslar baslamaz arka planda yap.
        QTimer.singleShot(0, self.refresh_engine)

    # ─── Engine detection (never blocks the Qt thread) ────────────

    def refresh_engine(self) -> None:
        """Probe engines on a worker thread and adopt the first available one."""
        if self._detecting:
            return
        self._detecting = True

        def _probe():
            found: LLMEngine | None = None
            for engine in self._engines:
                try:
                    if engine.is_available():
                        found = engine
                        break
                except Exception as e:
                    logger.debug("Engine %s probe failed: %s", engine.engine_name, e)
            self._engine_detected.emit(found)

        threading.Thread(target=_probe, daemon=True, name="LLMDetect").start()

    def _on_engine_detected(self, engine: object) -> None:
        """Runs on the Qt main thread — safe to touch signals/state."""
        self._detecting = False

        if engine is None:
            if self._active_engine is not None:
                logger.warning("Active LLM engine went away")
            else:
                logger.warning(
                    "No LLM engine available. Install Ollama or set ANTHROPIC_API_KEY."
                )
            self._active_engine = None
            self.engine_status.emit("No LLM available")
            # Bu tespit bekleyen bir istek icin yapildiysa, istegi asili
            # birakma — kullaniciya hata don.
            if self._retry_pending or self._pending_request is not None:
                self._emit_no_engine_error()
            return

        if engine is not self._active_engine:
            self._set_active_engine(engine)  # type: ignore[arg-type]

        # Motor tespiti bekleyen bir istek yuzunden tetiklendiyse sessizce tekrar dene.
        if self._retry_pending:
            self._retry_pending = False
            if self._pending_request is not None:
                message, image_b64 = self._pending_request
                self._pending_request = None
                logger.info("Retrying request after engine redetection")
                self._dispatch(message, image_b64, record_history=False)

    def _set_active_engine(self, engine: LLMEngine) -> None:
        """Set the active engine and connect its signals."""
        # Disconnect previous engine signals if any
        if self._active_engine is not None:
            try:
                self._active_engine.token_received.disconnect(self.token_received)
                self._active_engine.generation_complete.disconnect(self._on_generation_complete)
                self._active_engine.generation_error.disconnect(self._on_generation_error)
            except TypeError:
                pass

        self._active_engine = engine

        # Connect new engine signals
        engine.token_received.connect(self.token_received)
        engine.generation_complete.connect(self._on_generation_complete)
        engine.generation_error.connect(self._on_generation_error)

        logger.info("LLM engine active: %s", engine.engine_name)
        self.engine_status.emit(engine.engine_name)

    def generate(self, user_message: str, image_b64: str | None = None) -> None:
        """
        Generate a response to the user's message.

        Adds the message to conversation history, builds the full message list
        (system + history), and sends to the active engine.

        Args:
            user_message: The user's transcribed speech.
            image_b64: Optional base64 encoded image for vision requests.
        """
        # Sicak yolda ASLA is_available() cagirmiyoruz — o 2 sn timeout'lu bir
        # HTTP istegi ve Qt ana thread'ini blokluyordu. Elimizdeki motoru
        # kullan; yoksa/bozuksa yeniden tespit asenkron olarak tetiklenir.
        if self._active_engine is None:
            self._pending_request = (user_message, image_b64)
            self._retry_pending = True
            self.refresh_engine()

            if not self._detecting:
                # refresh_engine hicbir sey baslatmadiysa (imkansiza yakin) hata ver.
                self._emit_no_engine_error()
            else:
                logger.info("No active LLM engine — detecting, request queued")
            return

        self._dispatch(user_message, image_b64)

    def _dispatch(self, user_message: str, image_b64: str | None,
                  record_history: bool = True) -> None:
        """Build the message list and hand it to the active engine."""
        if self._active_engine is None:
            self._emit_no_engine_error()
            return

        # Add user message to history (without the image to save RAM)
        if record_history:
            self._history.append({"role": "user", "content": user_message})

        # Build full message list
        messages = [{"role": "system", "content": self._system_prompt}]

        # Deep copy the history to avoid modifying the deque items
        for h in self._history:
            messages.append(dict(h))

        # Attach image to the latest message if provided
        if image_b64:
            messages[-1]["images"] = [image_b64]

        logger.debug("Generating response via %s (context: %d messages)",
                      self._active_engine.engine_name, len(self._history))

        # Send to engine
        self._active_engine.generate(messages)

    def _emit_no_engine_error(self) -> None:
        model = config.get("llm", "ollama", "model", default="qwen2.5:3b")
        error = (
            "No LLM engine available. Please install Ollama and run: "
            f"ollama pull {model}"
        )
        logger.error(error)
        self._pending_request = None
        self._retry_pending = False
        self.generation_error.emit(error)

    def _on_generation_error(self, error: str) -> None:
        """
        Engine failed. If it looks like the server went away, redetect once and
        silently retry — otherwise surface the error.
        """
        looks_like_connection_loss = any(
            token in error.lower()
            for token in ("connection", "refused", "timed out", "timeout", "unreachable")
        )

        if looks_like_connection_loss and not self._retry_pending:
            last_user = next(
                (h["content"] for h in reversed(self._history) if h["role"] == "user"),
                None,
            )
            if last_user is not None:
                logger.warning("LLM connection lost — redetecting engine and retrying once")
                self._pending_request = (last_user, None)
                self._retry_pending = True
                self._active_engine = None
                self.refresh_engine()
                return

        self._pending_request = None
        self._retry_pending = False
        self.generation_error.emit(error)

    def _on_generation_complete(self, response: str) -> None:
        """Handle completed generation — save to history and forward signal."""
        self._pending_request = None
        self._retry_pending = False

        if response:
            self._history.append({"role": "assistant", "content": response})
            logger.debug("Context updated: %d messages in history", len(self._history))

        self.generation_complete.emit(response)

    def stop(self) -> None:
        """Stop any ongoing generation."""
        if self._active_engine:
            self._active_engine.stop()

    def clear_context(self) -> None:
        """Clear conversation history."""
        self._history.clear()
        logger.debug("Conversation context cleared")

    @property
    def active_engine_name(self) -> str:
        """Get the name of the currently active engine."""
        if self._active_engine:
            return self._active_engine.engine_name
        return "None"
