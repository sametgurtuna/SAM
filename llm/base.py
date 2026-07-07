# SAM — LLM Engine Base Class
# Abstract interface that all LLM engines must implement.

import logging

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class LLMEngine(QObject):
    """
    Base class for LLM engines.
    
    All engines must:
        - Accept a list of messages (conversation history)
        - Stream tokens via `token_received` signal
        - Emit `generation_complete` with full response when done
        - Report availability via `is_available()`
    
    Signals:
        token_received(str): Single token/chunk from the LLM stream.
        generation_complete(str): Full response text when generation finishes.
        generation_error(str): Error message if generation fails.
    """

    token_received = pyqtSignal(str)
    generation_complete = pyqtSignal(str)
    generation_error = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()

    def is_available(self) -> bool:
        """Check if this engine is ready to use (model loaded, API reachable, etc.)."""
        raise NotImplementedError

    def generate(self, messages: list[dict[str, str]]) -> None:
        """
        Generate a response from conversation messages. Runs in a background thread.
        
        Args:
            messages: List of dicts with 'role' and 'content' keys.
                      Roles: 'system', 'user', 'assistant'
        
        Must emit:
            - token_received(str) for each streaming chunk
            - generation_complete(str) with full response when done
            - generation_error(str) if something goes wrong
        """
        raise NotImplementedError

    def stop(self) -> None:
        """Cancel any ongoing generation."""
        raise NotImplementedError

    @property
    def engine_name(self) -> str:
        """Human-readable name of this engine (e.g., 'Ollama (qwen2.5:3b)')."""
        raise NotImplementedError
