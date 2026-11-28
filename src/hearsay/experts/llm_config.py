"""
Single source of LLM configuration.

Every script and knowledge source gets its LLM client from here instead of hardcoding a
base_url / model / token budget. Change the provider or model in ONE place (or via env vars)
and the whole project follows. This fixes the previous scatter where each script hardcoded
its own, inconsistent values.

Configuration precedence (highest first):
  1. explicit arguments to make_client(...)
  2. environment variables (see below)
  3. the DEFAULTS below

Environment variables:
  HEARSAY_LLM_BASE_URL   default https://api.deepseek.com/v1
  HEARSAY_LLM_MODEL      default deepseek-flash
  HEARSAY_LLM_API_KEY    the API key; falls back to DEEPSEEK_API_KEY for convenience
  HEARSAY_LLM_MAX_TOKENS default unset (server default); set an int to cap output
  HEARSAY_LLM_TIMEOUT    default 600 (seconds; reasoning models can be slow)

For a local model (LM Studio), set e.g.:
  HEARSAY_LLM_BASE_URL=http://localhost:1234/v1  HEARSAY_LLM_MODEL=<local-model>  (no key)
"""
import os

from hearsay.experts.llm_client import OpenAICompatClient

DEFAULTS = {
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-flash",
    "timeout": 600.0,
    "max_tokens": None,
}


def _env(name, fallback=None):
    val = os.environ.get(name)
    return val if val not in (None, "") else fallback


def get_api_key() -> str | None:
    """API key from HEARSAY_LLM_API_KEY, falling back to DEEPSEEK_API_KEY."""
    return _env("HEARSAY_LLM_API_KEY") or _env("DEEPSEEK_API_KEY")


def require_api_key() -> str:
    """Return the API key or exit with a clear message. For scripts that need a remote LLM."""
    key = get_api_key()
    if not key:
        raise SystemExit(
            "No LLM API key set. Set one of:\n"
            '  $env:HEARSAY_LLM_API_KEY = "sk-..."   (preferred)\n'
            '  $env:DEEPSEEK_API_KEY   = "sk-..."    (fallback)'
        )
    return key


def _env_bool(name):
    """Return True/False/None from an env var ('1','true','on' -> True; '0','false','off' ->
    False; unset -> None)."""
    v = _env(name)
    if v is None:
        return None
    return v.strip().lower() in ("1", "true", "on", "yes", "enabled")


def make_client(
    *,
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    max_tokens: int | None = None,
    timeout: float | None = None,
    thinking: bool | None = None,
) -> OpenAICompatClient:
    """Build a configured client. Explicit args win, then env vars, then DEFAULTS.

    thinking: whether the model's internal reasoning pass is enabled. Default (here) is
    DISABLED, which forces a reasoning model to externalize intermediate hypotheses into the
    visible output instead of hiding them in its reasoning trace. Override with the
    HEARSAY_LLM_THINKING env var, or pass thinking=True explicitly."""
    env_max = _env("HEARSAY_LLM_MAX_TOKENS")
    env_thinking = _env_bool("HEARSAY_LLM_THINKING")
    if thinking is None:
        thinking = env_thinking if env_thinking is not None else False
    return OpenAICompatClient(
        base_url=base_url or _env("HEARSAY_LLM_BASE_URL", DEFAULTS["base_url"]),
        model=model or _env("HEARSAY_LLM_MODEL", DEFAULTS["model"]),
        api_key=api_key if api_key is not None else get_api_key(),
        timeout=timeout if timeout is not None
                else float(_env("HEARSAY_LLM_TIMEOUT", DEFAULTS["timeout"])),
        max_tokens=max_tokens if max_tokens is not None
                   else (int(env_max) if env_max else DEFAULTS["max_tokens"]),
        thinking=thinking,
    )
