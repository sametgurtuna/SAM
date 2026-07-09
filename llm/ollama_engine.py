# SAM — Ollama LLM Engine
# Connects to a local Ollama instance for fully offline LLM inference.
# Uses the /api/chat endpoint with streaming for real-time token output.

import json
import logging
import threading

import requests

from core.config import config
from llm.base import LLMEngine

logger = logging.getLogger(__name__)

# Default Ollama API endpoint
DEFAULT_BASE_URL = "http://localhost:11434"
CHAT_ENDPOINT = "/api/chat"
TAGS_ENDPOINT = "/api/tags"


class OllamaEngine(LLMEngine):
    """
    LLM engine using a local Ollama instance.
    
    Ollama runs as a separate process on localhost:11434.
    This engine streams tokens via its REST API.
    
    Recommended models:
        - qwen2.5:3b   → Best quality/size ratio (~2GB RAM)
        - llama3.2:3b   → Good general purpose
        - phi3.5        → Strong reasoning (~2.5GB RAM)
        - gemma2:2b     → Lightweight option
    """

    def __init__(self) -> None:
        super().__init__()

        self._base_url: str = config.get("llm", "ollama", "base_url", default=DEFAULT_BASE_URL)
        self._model: str = config.get("llm", "ollama", "model", default="qwen2.5:3b")
        self._temperature: float = config.get("llm", "ollama", "temperature", default=0.7)
        self._max_tokens: int = config.get("llm", "ollama", "max_tokens", default=256)

        self._generating: bool = False
        self._thread: threading.Thread | None = None

        # Connection timeout for API calls
        self._timeout: int = 2
        # Generation timeout (per request, longer for actual generation)
        self._gen_timeout: int = 120

    @property
    def engine_name(self) -> str:
        return f"Ollama ({self._model})"

    def is_available(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            resp = requests.get(
                f"{self._base_url}{TAGS_ENDPOINT}",
                timeout=self._timeout
            )
            if resp.status_code != 200:
                return False

            # Check if our model is in the list
            data = resp.json()
            models = data.get("models", [])
            model_names = [m.get("name", "") for m in models]

            # Ollama model names can have tags like "qwen2.5:3b"
            # Check both exact match and base name match
            base_model = self._model.split(":")[0]
            for name in model_names:
                if name == self._model or name.startswith(f"{base_model}:"):
                    logger.info("Ollama available: model '%s' found", name)
                    return True

            logger.warning(
                "Ollama running but model '%s' not found. Available: %s",
                self._model, ", ".join(model_names) or "none"
            )
            logger.warning("Run: ollama pull %s", self._model)
            return False

        except requests.ConnectionError:
            logger.debug("Ollama not reachable at %s", self._base_url)
            return False
        except Exception as e:
            logger.debug("Ollama check failed: %s", e)
            return False

    def generate(self, messages: list[dict[str, str]]) -> None:
        """Generate a streaming response from Ollama."""
        if self._generating:
            logger.warning("Generation already in progress")
            return

        self._generating = True
        self._thread = threading.Thread(
            target=self._generate_worker,
            args=(messages,),
            daemon=True,
            name="OllamaThread"
        )
        self._thread.start()

    def stop(self) -> None:
        """Cancel ongoing generation."""
        self._generating = False

    def _generate_worker(self, messages: list[dict[str, str]]) -> None:
        """Background worker: stream tokens from Ollama API."""
        full_response = ""

        try:
            has_images = any("images" in m for m in messages)
            target_model = config.get("llm", "ollama", "vision_model", default="llava") if has_images else self._model

            if has_images:
                logger.info("Vision request detected, switching to vision model: %s", target_model)

            payload = {
                "model": target_model,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": self._temperature,
                    "num_predict": self._max_tokens,
                },
            }

            logger.debug("Ollama request: model=%s, messages=%d", self._model, len(messages))

            # Stream response
            with requests.post(
                f"{self._base_url}{CHAT_ENDPOINT}",
                json=payload,
                stream=True,
                timeout=self._gen_timeout,
            ) as resp:
                if resp.status_code != 200:
                    error_msg = f"Ollama API error: {resp.status_code} {resp.text[:200]}"
                    logger.error(error_msg)
                    self.generation_error.emit(error_msg)
                    return

                for line in resp.iter_lines(decode_unicode=True):
                    if not self._generating:
                        logger.debug("Generation cancelled by user")
                        break

                    if not line:
                        continue

                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Extract token from response
                    message = chunk.get("message", {})
                    token = message.get("content", "")

                    if token:
                        full_response += token
                        self.token_received.emit(token)

                    # Check if generation is complete
                    if chunk.get("done", False):
                        break

            logger.info("Ollama generation complete: %d chars", len(full_response))
            self.generation_complete.emit(full_response.strip())

        except requests.ConnectionError:
            error_msg = "Ollama connection lost. Is it still running?"
            logger.error(error_msg)
            self.generation_error.emit(error_msg)
        except requests.Timeout:
            error_msg = "Ollama request timed out"
            logger.error(error_msg)
            self.generation_error.emit(error_msg)
        except Exception as e:
            error_msg = f"Ollama generation failed: {e}"
            logger.error(error_msg)
            self.generation_error.emit(error_msg)
        finally:
            self._generating = False
