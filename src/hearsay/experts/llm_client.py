"""
LLM client interface and backends.

Knowledge sources depend only on the LLMClient interface (one method: complete). This lets
you swap a local model (LM Studio) for a hosted API (DeepSeek/Claude/OpenAI) without
touching any KS — they all speak the same OpenAI-compatible chat-completions shape.

OpenAICompatClient talks to any OpenAI-compatible /chat/completions endpoint — local
(LM Studio, default http://localhost:1234/v1, no key) or remote (DeepSeek/OpenAI, with a
base_url and api_key). Same class, different construction.
"""
from abc import ABC, abstractmethod
import json
import urllib.request
import urllib.error


class LLMClient(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Send a prompt, return the model's text response. Raises LLMError on failure."""
        ...


class LLMError(Exception):
    """Raised when the LLM call fails (network, bad status, unparseable response)."""


class OpenAICompatClient(LLMClient):
    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        model: str = "prism-ml/bonsai-27b",
        api_key: str | None = None,
        timeout: float = 120.0,
        temperature: float = 0.2,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.temperature = temperature

    def complete(self, prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        }
        data = json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM returned non-JSON envelope: {exc}") from exc

        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected LLM response shape: {exc}") from exc


# Backward-compatible alias: the local-only name used before the generalisation.
LocalLLMClient = OpenAICompatClient
