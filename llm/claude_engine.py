# SAM — Claude LLM Engine (Optional Cloud Fallback)
# Uses Anthropic's Claude API for high-quality responses.
# Only activated if ANTHROPIC_API_KEY is set and Ollama is unavailable.

import logging
import os
import threading

from core.config import config
from llm.base import LLMEngine

logger = logging.getLogger(__name__)


class ClaudeEngine(LLMEngine):
    """
    LLM engine using Anthropic's Claude API.
    
    Optional cloud fallback — only used when:
        1. Ollama is not available, AND
        2. ANTHROPIC_API_KEY environment variable is set
    
    Uses streaming for real-time token output.
    """

    def __init__(self) -> None:
        super().__init__()

        self._model: str = config.get("llm", "claude", "model", default="claude-sonnet-4-20250514")
        self._max_tokens: int = config.get("llm", "claude", "max_tokens", default=256)
        self._api_key: str | None = os.environ.get("ANTHROPIC_API_KEY")

        self._generating: bool = False
        self._thread: threading.Thread | None = None
        self._client = None

    @property
    def engine_name(self) -> str:
        return f"Claude ({self._model})"

    def is_available(self) -> bool:
        """Check if Claude API key is configured."""
        if not self._api_key:
            logger.debug("Claude API key not set (ANTHROPIC_API_KEY)")
            return False

        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self._api_key)
            logger.info("Claude API available: model '%s'", self._model)
            return True
        except ImportError:
            logger.debug("anthropic package not installed. Run: pip install anthropic")
            return False
        except Exception as e:
            logger.debug("Claude API check failed: %s", e)
            return False

    def generate(self, messages: list[dict[str, str]]) -> None:
        """Generate a streaming response from Claude API."""
        if self._generating:
            logger.warning("Generation already in progress")
            return

        self._generating = True
        self._thread = threading.Thread(
            target=self._generate_worker,
            args=(messages,),
            daemon=True,
            name="ClaudeThread"
        )
        self._thread.start()

    def stop(self) -> None:
        """Cancel ongoing generation."""
        self._generating = False

    def _generate_worker(self, messages: list[dict[str, str]]) -> None:
        """Background worker: stream tokens from Claude API."""
        full_response = ""

        try:
            import anthropic

            if self._client is None:
                self._client = anthropic.Anthropic(api_key=self._api_key)

            # Separate system message from conversation
            system_prompt = ""
            chat_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                else:
                    chat_messages.append(msg)

            logger.debug("Claude request: model=%s, messages=%d", self._model, len(chat_messages))

            # Stream response
            with self._client.messages.stream(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=chat_messages,
            ) as stream:
                for token in stream.text_stream:
                    if not self._generating:
                        logger.debug("Generation cancelled by user")
                        break

                    if token:
                        full_response += token
                        self.token_received.emit(token)

            logger.info("Claude generation complete: %d chars", len(full_response))
            self.generation_complete.emit(full_response.strip())

        except Exception as e:
            error_msg = f"Claude generation failed: {e}"
            logger.error(error_msg)
            self.generation_error.emit(error_msg)
        finally:
            self._generating = False
