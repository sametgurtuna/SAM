# SAM — LLM Router
# Auto-detects the best available LLM engine and manages conversation context.
# Priority: Ollama (local, free) → Claude (cloud, paid) → None (error)

import logging
from collections import deque

from PyQt6.QtCore import QObject, pyqtSignal

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

        # Detect best engine
        self._detect_engine()

    def _detect_engine(self) -> None:
        """Find the first available LLM engine."""
        for engine in self._engines:
            if engine.is_available():
                self._set_active_engine(engine)
                return

        logger.warning("No LLM engine available. Install Ollama or set ANTHROPIC_API_KEY.")
        self._active_engine = None
        self.engine_status.emit("No LLM available")

    def _set_active_engine(self, engine: LLMEngine) -> None:
        """Set the active engine and connect its signals."""
        # Disconnect previous engine signals if any
        if self._active_engine is not None:
            try:
                self._active_engine.token_received.disconnect(self.token_received)
                self._active_engine.generation_complete.disconnect(self._on_generation_complete)
                self._active_engine.generation_error.disconnect(self.generation_error)
            except TypeError:
                pass

        self._active_engine = engine

        # Connect new engine signals
        engine.token_received.connect(self.token_received)
        engine.generation_complete.connect(self._on_generation_complete)
        engine.generation_error.connect(self.generation_error)

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
        # If no engine, try re-detecting (maybe Ollama was started)
        if self._active_engine is None or not self._active_engine.is_available():
            self._detect_engine()

        if self._active_engine is None:
            error = "No LLM engine available. Please install Ollama and run: ollama pull qwen2.5:3b"
            logger.error(error)
            self.generation_error.emit(error)
            return

        # Add user message to history (without the image to save RAM)
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

    def _on_generation_complete(self, response: str) -> None:
        """Handle completed generation — save to history and forward signal."""
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
