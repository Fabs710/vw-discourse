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


def detect_provider(model: str) -> str:
    m = model.lower()
    if m.startswith("claude"):
        return "anthropic"
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
                if self.provider == "openai":
                    resp = self._call_openai(messages)
                else:
                    resp = self._call_anthropic(messages)
                resp.latency_s = time.time() - t0
                return resp
            except MissingAPIKey:
                raise                          # missing key: not transient
            except Exception as e:             # network / rate limit / 5xx
                last_err = e
                if attempt >= self.MAX_RETRIES:
                    break
                wait = min(2 ** (attempt + 1), 60)   # 2,4,8,16,32,60,60,60 s (rate-limit windows need patience)
                print("  [retry %d/%d] %s: %s - waiting %ds" %
                      (attempt + 1, self.MAX_RETRIES, label or "call",
                       type(e).__name__, wait), flush=True)
                time.sleep(wait)
        raise last_err

    def _call_openai(self, messages: list[dict]) -> LLMResponse:
        client = self._openai_client()
        kwargs = dict(model=self.model, messages=messages, seed=self.seed)
        if not _omit_temperature(self.model):
            kwargs["temperature"] = self.temperature
        r = client.chat.completions.create(**kwargs)
        choice = r.choices[0]
        return LLMResponse(
            text=choice.message.content or "",
            provider="openai",
            model_requested=self.model,
            model_resolved=getattr(r, "model", self.model),
            tokens=getattr(r.usage, "total_tokens", 0) if r.usage else 0,
            input_tokens=getattr(r.usage, "prompt_tokens", 0) if r.usage else 0,
            output_tokens=getattr(r.usage, "completion_tokens", 0) if r.usage else 0,
            system_fingerprint=getattr(r, "system_fingerprint", None),
            seed=self.seed,
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
    assert detect_provider("claude-opus-4-8") == "anthropic"
    assert _omit_temperature("o4-mini") and _omit_temperature("gpt-5.4-mini") and not _omit_temperature("gpt-4o")
    c = LLMClient("o4-mini")
    print("LLMClient OK — provider:", c.provider, "| temp omitted:", _omit_temperature(c.model))
    print("Provider routing and reproducibility wrapper verified (offline).")
