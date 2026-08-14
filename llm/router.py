# SAM — LLM Router
# Intent-based engine selection, dynamic prompt construction, and RAG integration.
# Pipeline: classify intent → select mode → retrieve knowledge → build prompt → route to engine

import logging
import os
import threading
from collections import deque
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from core.config import config
from core import paths
from llm.base import LLMEngine
from llm.ollama_engine import OllamaEngine
from llm.claude_engine import ClaudeEngine
from llm.intent import Intent, IntentClassifier
from llm.prompt_builder import PromptBuilder
from llm.memory import create_memory_store

if TYPE_CHECKING:
    from llm.rag import RAGEngine

logger = logging.getLogger(__name__)


class LLMRouter(QObject):
    """
    Routes LLM requests to the best available engine.

    Architecture:
        1. IntentClassifier → NORMAL / FENERBAHCE / COMPLEX
        2. PromptBuilder    → persona + rules + mode + RAG context
        3. Engine selection → Ollama (local) or Claude (cloud)

    NORMAL / FENERBAHCE → Ollama (local, fast)
    COMPLEX             → Claude (cloud, high-reasoning)
    Fallback            → Currently available engine

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

    # Internal: worker thread -> Qt main thread
    _engines_probed = pyqtSignal(bool, bool)  # (ollama_available, claude_available)

    def __init__(self) -> None:
        super().__init__()

        self._max_context: int = config.get("llm", "context_window", default=8)

        # ── Subsystems ────────────────────────────────────────────
        self._classifier = IntentClassifier()
        self._prompt_builder = PromptBuilder()
        self._memory = create_memory_store()

        # RAG — lazy init, loaded only when needed
        self._rag = None
        self._rag_enabled: bool = config.get("llm", "rag", "enabled", default=True)

        # ── Conversation history ──────────────────────────────────
        self._history: deque[dict[str, str]] = deque(maxlen=self._max_context * 2)

        # ── Dual engine setup ─────────────────────────────────────
        # Both engines instantiated; availability monitored independently
        self._ollama = OllamaEngine()
        self._claude = ClaudeEngine()
        self._ollama_available: bool = False
        self._claude_available: bool = False

        # Active engine tracking for signal wiring
        self._active_engine: LLMEngine | None = None

        self._detecting: bool = False
        self._retry_pending: bool = False
        self._pending_request: tuple[str, str | None] | None = None

        # Intent selected for this turn
        self._current_intent: Intent = Intent.NORMAL

        self._engines_probed.connect(self._on_engines_probed)

        # Probe engines in background once event loop starts
        QTimer.singleShot(0, self.refresh_engines)

    # ─── Engine detection ─────────────────────────────────────────

    def refresh_engines(self) -> None:
        """Probe both engines on a worker thread."""
        if self._detecting:
            return
        self._detecting = True

        def _probe():
            ollama_ok = False
            claude_ok = False
            try:
                ollama_ok = self._ollama.is_available()
            except Exception as e:
                logger.debug("Ollama probe failed: %s", e)
            try:
                claude_ok = self._claude.is_available()
            except Exception as e:
                logger.debug("Claude probe failed: %s", e)
            self._engines_probed.emit(ollama_ok, claude_ok)

        threading.Thread(target=_probe, daemon=True, name="LLMDetect").start()

    # Backward compatibility — OllamaService called refresh_engine()
    def refresh_engine(self) -> None:
        self.refresh_engines()

    def _on_engines_probed(self, ollama_ok: bool, claude_ok: bool) -> None:
        """Runs on Qt main thread — safe to mutate state and emit signals."""
        self._detecting = False
        self._ollama_available = ollama_ok
        self._claude_available = claude_ok

        # Status report
        available = []
        if ollama_ok:
            available.append(self._ollama.engine_name)
        if claude_ok:
            available.append(self._claude.engine_name)

        if available:
            logger.info("LLM engines available: %s", ", ".join(available))
            self.engine_status.emit(available[0])  # Report primary engine
        else:
            logger.warning("No LLM engine available. Install Ollama or set ANTHROPIC_API_KEY.")
            self.engine_status.emit("No LLM available")
            if self._retry_pending or self._pending_request is not None:
                self._emit_no_engine_error()
            return

        # Retry queued request if pending
        if self._retry_pending:
            self._retry_pending = False
            if self._pending_request is not None:
                message, image_b64 = self._pending_request
                self._pending_request = None
                logger.info("Retrying request after engine redetection")
                self._dispatch(message, image_b64, record_history=False)

    def _select_engine(self, intent: Intent) -> LLMEngine | None:
        """
        Select engine based on intent.
        Ollama is the primary local engine. Claude is used when configured
        for complex tasks.
        """
        if intent == Intent.COMPLEX and self._claude_available:
            return self._claude

        if self._ollama_available:
            return self._ollama

        # Fallback to Claude if Ollama is unavailable but API key exists
        if self._claude_available:
            logger.info("Ollama unavailable — using Claude (API key configured)")
            return self._claude

        return None

    def _connect_engine(self, engine: LLMEngine) -> None:
        """Switch active engine and wire signals."""
        if self._active_engine is engine:
            return

        # Disconnect previous engine signals
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

    # ─── Generation ───────────────────────────────────────────────

    def generate(self, user_message: str, image_b64: str | None = None,
                 language: str | None = None) -> None:
        """
        Generate a response to the user's message.

        Pipeline:
          1. Classify intent (NORMAL / FENERBAHCE / COMPLEX)
          2. Set mode
          3. Select engine
          4. Dispatch

        Args:
            language: Detected speech language code ("tr"/"en") for output alignment.
        """
        # 1. Intent classification
        result = self._classifier.classify(user_message)
        self._current_intent = result.intent
        logger.info("Intent: %s (confidence: %.2f)", result.intent.value, result.confidence)

        # 2. Select engine
        engine = self._select_engine(result.intent)

        if engine is None:
            # No engine available — queue request and re-probe
            self._pending_request = (user_message, image_b64)
            self._retry_pending = True
            self.refresh_engines()
            if not self._detecting:
                self._emit_no_engine_error()
            else:
                logger.info("No active LLM engine — detecting, request queued")
            return

        # 3. Connect engine
        self._connect_engine(engine)
        logger.info("Routing to %s", engine.engine_name)

        # 4. Dispatch
        self._dispatch(user_message, image_b64, language=language)

    def _dispatch(self, user_message: str, image_b64: str | None,
                  record_history: bool = True, language: str | None = None) -> None:
        """Build the message list and hand it to the active engine."""
        if self._active_engine is None:
            self._emit_no_engine_error()
            return

        # Record to history (image omitted to save RAM)
        if record_history:
            self._history.append({"role": "user", "content": user_message})

        # ── RAG retrieval (domain intents) ───────────────────────
        knowledge = None
        if self._current_intent == Intent.FENERBAHCE and self._rag_enabled:
            knowledge = self._get_rag_knowledge(user_message)

        # ── Memory context summary ────────────────────────────────
        memory = self._memory.get_context_summary()

        # ── Mode determination ────────────────────────────────────
        mode = None
        if self._current_intent == Intent.FENERBAHCE:
            mode = "FENERBAHCE"

        # ── System prompt ─────────────────────────────────────────
        system_prompt = self._prompt_builder.build(
            mode=mode,
            knowledge=knowledge,
            memory=memory,
            language=language,
        )

        # ── Messages payload ──────────────────────────────────────
        messages = [{"role": "system", "content": system_prompt}]

        for h in self._history:
            messages.append(dict(h))

        # Attach image for vision
        if image_b64:
            messages[-1]["images"] = [image_b64]

        logger.debug("Generating response via %s (context: %d messages, mode: %s)",
                      self._active_engine.engine_name, len(self._history),
                      mode or "NORMAL")

        self._active_engine.generate(messages)

    def _ensure_rag_constructed(self) -> "RAGEngine | None":
        """Instantiate RAGEngine if not already created (lazy)."""
        if self._rag is not None:
            return self._rag

        try:
            from llm.rag import RAGEngine

            knowledge_path = config.get(
                "llm", "rag", "knowledge_path", default=""
            ) or os.path.join(paths.resource_root(), "knowledge")
            embedding_model = config.get(
                "llm", "rag", "embedding_model",
                default="all-MiniLM-L6-v2",
            ) or "all-MiniLM-L6-v2"
            top_k = config.get("llm", "rag", "top_k", default=3) or 3
            chunk_size = config.get("llm", "rag", "chunk_size", default=800) or 800
            chunk_overlap = config.get("llm", "rag", "chunk_overlap", default=80) or 80

            self._rag = RAGEngine(
                knowledge_path=knowledge_path,
                embedding_model=embedding_model,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                top_k=top_k,
            )
            logger.info(
                "RAG engine created (path=%s, chunk_size=%d) — lazy init on first use",
                knowledge_path, chunk_size,
            )
        except ImportError as e:
            logger.warning(
                "RAG dependencies not installed (sentence-transformers, chromadb): %s", e
            )
            self._rag_enabled = False
            return None

        return self._rag

    def _get_rag_knowledge(self, query: str) -> str | None:
        """Retrieve context from RAG. Loads models on first invocation."""
        rag = self._ensure_rag_constructed()
        if rag is None:
            return None
        return rag.retrieve(query)

    def warm_rag(self) -> None:
        """
        Pre-warm RAG engine (embedding model + vector index) in the background
        to eliminate first-query loading latency.
        """
        if not self._rag_enabled:
            return
        rag = self._ensure_rag_constructed()
        if rag is not None:
            rag.warm()

    # ─── Error handling ───────────────────────────────────────────

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
                logger.warning("LLM connection lost — redetecting engines and retrying once")
                self._pending_request = (last_user, None)
                self._retry_pending = True
                self._active_engine = None
                self.refresh_engines()
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

    # ─── Public API ───────────────────────────────────────────────

    def stop(self) -> None:
        """Stop any ongoing generation."""
        if self._active_engine:
            self._active_engine.stop()

    def clear_context(self) -> None:
        """Clear conversation history."""
        self._history.clear()
        logger.debug("Conversation context cleared")

    def remember(self, category: str, key: str, value: str) -> None:
        """Persist a piece of information into long-term memory (see llm/memory.py)."""
        self._memory.store(key, value, category)

    @property
    def active_engine_name(self) -> str:
        """Get the name of the currently active engine."""
        if self._active_engine:
            return self._active_engine.engine_name
        return "None"
