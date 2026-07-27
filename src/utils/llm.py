"""
src/utils/llm.py — provider-agnostic LLM client with reproducibility metadata.

One `LLMClient` dispatches to OpenAI or Anthropic based on the model name, so the
same engine can run the cross-model comparison without changes. Every call returns
an `LLMResponse` carrying the reproducibility metadata the thesis needs: the
resolved model snapshot, the system fingerprint (OpenAI), the seed, token counts,
and finish reason.

Design notes:
    - Clients are created lazily, so importing this module never requires API keys
      (unit tests and offline checks work without a network).
    - o-series and gpt-5-family OpenAI reasoning models do not accept a custom
      temperature; it is omitted automatically.
    - OpenAI calls are sent WITHOUT an output cap (API default applies); max_tokens
      caps Anthropic calls, where the parameter is mandatory.
    - Anthropic has no seed/system_fingerprint; those fields come back as None and
      the limitation is recorded rather than hidden.
"""

from __future__ import annotations
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


class MissingAPIKey(RuntimeError):
    """Raised when the required API key is not configured (never retried)."""


def _is_permanent(err: Exception) -> bool:
    """True for failures that no amount of waiting will fix.

    The retry loop exists for dropped connections, rate limits and 5xx. Retrying a
    rejected key or a misspelled model id just burns 4 minutes of backoff before
    reporting the same error - which is exactly what happens while configuring a new
    judge, when typos are most likely. 429 stays transient: rate limits do clear.
    """
    if isinstance(err, (ImportError, ModuleNotFoundError)):
        return True
    status = getattr(err, "status_code", None) or getattr(getattr(err, "response", None), "status_code", None)
    if status in (400, 401, 403, 404, 422):
        return True
    name = type(err).__name__
    return name in ("AuthenticationError", "PermissionDeniedError", "NotFoundError",
                    "BadRequestError", "UnprocessableEntityError")


@dataclass
class LLMResponse:
    text: str
    provider: str
    model_requested: str
    model_resolved: str            # the concrete snapshot the API actually used
    tokens: int
    system_fingerprint: Optional[str]
    seed: Optional[int]
    finish_reason: Optional[str]
    latency_s: float
    input_tokens: int = 0
    output_tokens: int = 0

    def meta(self) -> dict:
        """Reproducibility metadata for per-call logging."""
        return {
            "provider": self.provider,
            "model_requested": self.model_requested,
            "model_resolved": self.model_resolved,
            "system_fingerprint": self.system_fingerprint,
            "seed": self.seed,
            "finish_reason": self.finish_reason,
            "tokens": self.tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "latency_s": round(self.latency_s, 2),
        }


# ── OpenAI-compatible third-party endpoints ──────────────────────────────────
# Google and the open-weight hosts all expose an OpenAI-compatible chat-completions
# API. Routing them through the existing OpenAI code path rather than writing a new
# provider per vendor is deliberate: that path has already executed several thousand
# scored calls in this study, so a third or fourth judge inherits its retry logic,
# its token accounting and its finish-reason handling instead of re-implementing
# them. Only the base URL and the key change.
#
# Each entry: prefix -> (provider label, env var holding the key, base URL)
COMPATIBLE = {
    # bare vendor names -> that vendor's own OpenAI-compatible endpoint
    "gemini":  ("google",   "GOOGLE_API_KEY",
                "https://generativelanguage.googleapis.com/v1beta/openai/"),
    # bare open-weight names -> whichever host OPENWEIGHT_BASE_URL points at
    "qwen":    ("openweight", "OPENWEIGHT_API_KEY", None),
    "llama":   ("openweight", "OPENWEIGHT_API_KEY", None),
    "deepseek":("openweight", "OPENWEIGHT_API_KEY", None),
    "mistral": ("openweight", "OPENWEIGHT_API_KEY", None),
    # any 'vendor/model' slug -> an aggregator (OpenRouter, Together, ...)
    "_aggregator": ("openweight", "OPENWEIGHT_API_KEY", None),
}


def _compatible_entry(model: str):
    """Which OpenAI-compatible endpoint, if any, serves this model name.

    Two naming conventions are in play and they route differently:

      'gemini-3.1-pro'         bare name  -> the vendor's own endpoint (Google)
      'google/gemini-3.1-pro'  slug form  -> an aggregator such as OpenRouter

    A slash means an aggregator by definition: OpenRouter, Together and the rest
    all namespace their catalogue as vendor/model, and the request goes to THEIR
    endpoint with THEIR key regardless of who trained the model. Matching only on
    a bare prefix would have sent 'google/gemini-3.1-pro' down the OpenAI path
    with an OpenAI key, which fails with an unhelpful authentication error.
    """
    m = model.lower()
    # Google's REST catalogue prefixes every id with 'models/' - that is its own naming,
    # not an aggregator namespace, and it is exactly the form a user copies out of a
    # model listing. Strip it before the slash rule, or 'models/gemini-3.6-flash' routes
    # to the open-weight host and fails on a key it was never meant to use.
    if m.startswith("models/"):
        m = m[len("models/"):]
    if "/" in m:
        return COMPATIBLE["_aggregator"]
    for prefix, entry in COMPATIBLE.items():
        if prefix != "_aggregator" and m.startswith(prefix):
            return entry
    return None


def detect_provider(model: str) -> str:
    m = model.lower()
    if m.startswith("claude"):
        return "anthropic"
    entry = _compatible_entry(m)
    if entry:
        return entry[0]
    if m.startswith(("gpt", "o1", "o3", "o4", "chatgpt")):
        return "openai"
    return "openai"  # sensible default


def _omit_temperature(model: str) -> bool:
    """Current reasoning models reject a custom temperature (OpenAI o-series and
    gpt-5 family; Anthropic claude-sonnet-5 / opus-4 / fable generations)."""
    return model.lower().startswith(
        ("o1", "o3", "o4", "gpt-5", "claude-sonnet-5", "claude-opus-4", "claude-fable"))


class LLMClient:
    """A thin, reproducibility-aware wrapper over OpenAI and Anthropic chat APIs."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        seed: int = 20260714,
        max_tokens: int = 2048,
    ):
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self.max_tokens = max_tokens
        self.provider = detect_provider(model)
        self._openai = None
        self._anthropic = None
        # Load .env from the project root (three levels up: src/utils/llm.py -> root)
        load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    # ── lazy clients ─────────────────────────────────────────────────────────
    def _openai_client(self):
        if self._openai is None:
            from openai import OpenAI
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                raise MissingAPIKey("OPENAI_API_KEY not set (see .env.example).")
            self._openai = OpenAI(api_key=key)
        return self._openai

    def _anthropic_client(self):
        if self._anthropic is None:
            from anthropic import Anthropic
            key = os.getenv("ANTHROPIC_API_KEY")
            if not key:
                raise MissingAPIKey("ANTHROPIC_API_KEY not set (see .env.example).")
            self._anthropic = Anthropic(api_key=key)
        return self._anthropic

    def _compatible_client(self):
        """OpenAI SDK pointed at a third-party OpenAI-compatible endpoint."""
        if self._openai is None:
            from openai import OpenAI
            entry = _compatible_entry(self.model)
            _, env_key, base = entry
            key = os.getenv(env_key)
            if not key:
                raise MissingAPIKey("%s not set (see .env.example)." % env_key)
            base = base or os.getenv("OPENWEIGHT_BASE_URL")
            if not base:
                raise MissingAPIKey(
                    "OPENWEIGHT_BASE_URL not set - give the OpenAI-compatible base URL of "
                    "whichever host serves %r (Together, Fireworks, DeepInfra, OpenRouter, ...)."
                    % self.model)
            self._openai = OpenAI(api_key=key, base_url=base)
        return self._openai

    # ── unified call (with retry on transient failures) ─────────────────────
    MAX_RETRIES = 8
    def call(self, messages: list[dict], label: str = "") -> LLMResponse:
        """messages: [{"role": "system"|"user"|"assistant", "content": str}, ...]

        Transient failures (dropped connections, timeouts, rate limits, 5xx)
        are retried with exponential backoff; a missing API key fails fast."""
        t0 = time.time()
        last_err = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                if self.provider == "anthropic":
                    resp = self._call_anthropic(messages)
                else:
                    resp = self._call_openai(messages)
                resp.latency_s = time.time() - t0
                return resp
            except MissingAPIKey:
                raise                          # missing key: not transient
            except Exception as e:             # network / rate limit / 5xx
                last_err = e
                if _is_permanent(e):
                    print("  [%s] permanent error, not retrying: %s: %s"
                          % (label or "call", type(e).__name__, e), flush=True)
                    raise
                if attempt >= self.MAX_RETRIES:
                    break
                wait = min(2 ** (attempt + 1), 60)   # 2,4,8,16,32,60,60,60 s (rate-limit windows need patience)
                print("  [retry %d/%d] %s: %s - waiting %ds" %
                      (attempt + 1, self.MAX_RETRIES, label or "call",
                       type(e).__name__, wait), flush=True)
                time.sleep(wait)
        raise last_err

    def _call_openai(self, messages: list[dict]) -> LLMResponse:
        # Serves OpenAI proper and every OpenAI-compatible endpoint (Google, open-weight
        # hosts). Two parameters are not universally supported by the compatible layers
        # and are omitted there rather than risking a 400: `seed`, and any temperature
        # the model would reject anyway.
        compatible = _compatible_entry(self.model) is not None
        client = self._compatible_client() if compatible else self._openai_client()
        kwargs = dict(model=self.model, messages=messages)
        if not compatible:
            kwargs["seed"] = self.seed
        if not _omit_temperature(self.model):
            kwargs["temperature"] = self.temperature
        r = client.chat.completions.create(**kwargs)
        choice = r.choices[0]
        return LLMResponse(
            text=choice.message.content or "",
            provider=self.provider,
            model_requested=self.model,
            model_resolved=getattr(r, "model", self.model),
            tokens=getattr(r.usage, "total_tokens", 0) if r.usage else 0,
            input_tokens=getattr(r.usage, "prompt_tokens", 0) if r.usage else 0,
            output_tokens=getattr(r.usage, "completion_tokens", 0) if r.usage else 0,
            system_fingerprint=getattr(r, "system_fingerprint", None),
            seed=None if compatible else self.seed,
            finish_reason=getattr(choice, "finish_reason", None),
            latency_s=0.0,
        )

    def _call_anthropic(self, messages: list[dict]) -> LLMResponse:
        client = self._anthropic_client()
        # Anthropic takes the system prompt separately and only user/assistant turns.
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        convo = [m for m in messages if m["role"] in ("user", "assistant")]
        kwargs = dict(
            model=self.model,
            system=system or None,
            messages=convo,
            max_tokens=self.max_tokens,
        )
        if not _omit_temperature(self.model):
            kwargs["temperature"] = self.temperature
        r = client.messages.create(**kwargs)
        text = "".join(getattr(b, "text", "") for b in r.content if getattr(b, "type", "") == "text")
        usage = getattr(r, "usage", None)
        in_t = usage.input_tokens if usage else 0
        out_t = usage.output_tokens if usage else 0
        return LLMResponse(
            text=text,
            provider="anthropic",
            model_requested=self.model,
            model_resolved=getattr(r, "model", self.model),
            tokens=in_t + out_t,
            input_tokens=in_t,
            output_tokens=out_t,
            system_fingerprint=None,          # not provided by Anthropic
            seed=None,                          # Anthropic has no seed
            finish_reason=getattr(r, "stop_reason", None),
            latency_s=0.0,
        )


# ── offline self-test: python src/utils/llm.py ───────────────────────────────
if __name__ == "__main__":
    assert detect_provider("o4-mini") == "openai"
    assert detect_provider("gpt-4o") == "openai"
    assert detect_provider("gpt-5.4-mini-2026-03-17") == "openai"
    assert detect_provider("claude-opus-4-8") == "anthropic"
    assert detect_provider("claude-sonnet-5") == "anthropic"
    # audit judges route through the OpenAI-compatible path, not a new provider
    assert detect_provider("gemini-3.1-pro") == "google"
    assert detect_provider("qwen3.6-27b") == "openweight"
    assert detect_provider("llama-4-70b-instruct") == "openweight"
    assert detect_provider("deepseek-v3") == "openweight"
    # aggregator slugs route to the aggregator, whoever trained the model
    assert detect_provider("qwen/qwen3.6-27b") == "openweight"
    assert detect_provider("google/gemini-3.1-pro") == "openweight"
    assert _compatible_entry("google/gemini-3.1-pro")[1] == "OPENWEIGHT_API_KEY"
    assert _compatible_entry("gemini-3.1-pro")[1] == "GOOGLE_API_KEY"
    assert detect_provider("meta-llama/llama-4-70b-instruct") == "openweight"
    # a Google catalogue id pasted verbatim must still reach Google
    assert detect_provider("models/gemini-3.6-flash") == "google"
    assert _compatible_entry("models/gemini-3.6-flash")[1] == "GOOGLE_API_KEY"
    assert detect_provider("models/gemini-2.5-pro") == "google"
    # a Claude model must never be captured by the compatible table
    assert _compatible_entry("claude-sonnet-5") is None
    assert _compatible_entry("gpt-5.4-mini") is None
    assert _compatible_entry("gemini-3.1-pro")[1] == "GOOGLE_API_KEY"
    assert _omit_temperature("o4-mini") and _omit_temperature("gpt-5.4-mini") and not _omit_temperature("gpt-4o")
    # constructing a client must not require a key (lazy) for any provider
    for m in ("o4-mini", "claude-sonnet-5", "gemini-3.1-pro", "qwen3.6-235b-instruct"):
        print("   %-26s -> provider %s" % (m, LLMClient(m).provider))
    print("Provider routing, compatible-endpoint table and reproducibility wrapper verified (offline).")
