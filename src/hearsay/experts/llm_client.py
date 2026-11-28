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
import time
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
        max_tokens: int | None = None,
        thinking: bool | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens   # None -> server default; set high for deep eval runs
        # thinking: None -> omit the field (provider default); True/False -> explicitly
        # enable/disable the model's internal reasoning pass. Disabling it forces the model
        # to externalize intermediate steps into the visible output (DeepSeek-specific field;
        # harmlessly ignored by endpoints that don't support it only if they tolerate extra
        # body keys — so it is omitted entirely when None).
        self.thinking = thinking

    def complete(self, prompt: str) -> str:
        """Return just the text. Used by knowledge sources."""
        text, _usage = self.complete_with_usage(prompt)
        return text

    def complete_with_usage(self, prompt: str) -> tuple[str, dict]:
        """Return (text, usage) where usage is {'prompt_tokens', 'completion_tokens',
        'total_tokens'}. Used by the evaluation harness to measure cost. Missing usage
        fields default to 0 (some local servers omit them)."""
        url = f"{self.base_url}/chat/completions"
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        }
        if self.max_tokens is not None:
            body["max_tokens"] = self.max_tokens
        if self.thinking is not None:
            body["thinking"] = {"type": "enabled" if self.thinking else "disabled"}
        data = json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Retry transient network failures (dropped connections, timeouts) a few times with
        # backoff before giving up. Long reasoning-model calls are especially prone to the
        # server closing an idle-looking connection mid-stream.
        payload = None
        last_exc = None
        for attempt in range(4):
            request = urllib.request.Request(url, data=data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except (urllib.error.URLError, TimeoutError, ConnectionError,
                    json.JSONDecodeError) as exc:
                last_exc = exc
                if attempt < 3:
                    time.sleep(2 ** attempt)   # 1s, 2s, 4s backoff
        if payload is None:
            raise LLMError(f"LLM request failed after retries: {last_exc}") from last_exc

        try:
            text = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected LLM response shape: {exc}") from exc

        raw_usage = payload.get("usage") or {}
        try:
            finish_reason = payload["choices"][0].get("finish_reason")
        except (KeyError, IndexError, TypeError):
            finish_reason = None
        # Thinking/reasoning models (e.g. deepseek-reasoner) spend "reasoning tokens" on an
        # internal chain-of-thought BEFORE the visible answer. These are usually reported in
        # completion_tokens_details.reasoning_tokens. Capture them: they are the real cost of
        # the model's reasoning and are often far larger than the visible completion.
        details = raw_usage.get("completion_tokens_details") or {}
        reasoning_tokens = details.get("reasoning_tokens", 0)
        usage = {
            "prompt_tokens": raw_usage.get("prompt_tokens", 0),
            "completion_tokens": raw_usage.get("completion_tokens", 0),
            "reasoning_tokens": reasoning_tokens,
            "total_tokens": raw_usage.get("total_tokens", 0),
            # "stop" = model finished naturally; "length" = truncated by the token budget.
            "finish_reason": finish_reason,
        }
        return text, usage


# Backward-compatible alias: the local-only name used before the generalisation.
LocalLLMClient = OpenAICompatClient
