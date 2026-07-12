#!/usr/bin/env python3
"""
ai_client.py — Unified Multi-Provider AI Interface

Single interface for Anthropic Claude, OpenAI GPT, Google Gemini, DeepSeek.

Usage:
    from ai_client import AIClient

    client = AIClient(
        provider="anthropic",
        api_key="sk-ant-xxx",
        model="claude-sonnet-4-5"
    )

    response, usage = client.chat(
        system="You are a PLC engineer...",
        user="Analyze this code: ...",
        max_tokens=4096,
        on_chunk=lambda text: print(text, end="")  # for streaming
    )
    print(f"Token usage: {usage}")
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional


# =========================================================================
# Provider catalog
# =========================================================================

PROVIDER_CATALOG = {
    "anthropic": {
        "display": "Anthropic Claude",
        "models": [
            "claude-opus-4-8",                # Opus 4.8 (most powerful, 2026)
            "claude-sonnet-4-6",              # Sonnet 4.6 (default — balanced)
            "claude-sonnet-4-5-20250929",     # Sonnet 4.5 (legacy snapshot)
            "claude-haiku-4-5-20251001",      # Haiku 4.5 (fast, cheap)
            "claude-opus-4-5-20250929",       # Opus 4.5 (previous major)
        ],
        "default_model": "claude-sonnet-4-6",
        "supports_streaming": True,
        "key_url": "https://console.anthropic.com/settings/keys",
        "key_prefix": "sk-ant-",
        # Pricing per 1M tokens (approximate, as of 2026-05, USD)
        "pricing": {
            "claude-opus-4-8":               {"input": 15.00, "output": 75.00},
            "claude-sonnet-4-6":             {"input": 3.00,  "output": 15.00},
            "claude-sonnet-4-5-20250929":    {"input": 3.00,  "output": 15.00},
            "claude-haiku-4-5-20251001":     {"input": 0.80,  "output": 4.00},
            "claude-opus-4-5-20250929":      {"input": 15.00, "output": 75.00},
        },
    },
    "openai": {
        "display": "OpenAI GPT",
        "models": [
            "gpt-5",                          # GPT-5 (2026 flagship)
            "gpt-4.5",                        # GPT-4.5 (mid-tier)
            "gpt-4o",                         # GPT-4o
            "gpt-4o-mini",                    # GPT-4o-mini (cheap)
            "o3",                             # o3 reasoning
            "o3-mini",                        # o3-mini (cheap reasoning)
            "o1",                             # o1 (legacy reasoning)
        ],
        "default_model": "gpt-4o",
        "supports_streaming": True,
        "key_url": "https://platform.openai.com/api-keys",
        "key_prefix": "sk-",
        "pricing": {
            "gpt-5":         {"input": 10.00, "output": 30.00},
            "gpt-4.5":       {"input": 5.00,  "output": 15.00},
            "gpt-4o":        {"input": 2.50,  "output": 10.00},
            "gpt-4o-mini":   {"input": 0.15,  "output": 0.60},
            "o3":            {"input": 20.00, "output": 80.00},
            "o3-mini":       {"input": 3.00,  "output": 12.00},
            "o1":            {"input": 15.00, "output": 60.00},
        },
    },
    "google": {
        "display": "Google Gemini",
        "models": [
            "gemini-3.5-flash",              # Gemini 3.5 Flash (GA — near-Pro at Flash cost)
            "gemini-2.5-pro",                # Gemini 2.5 Pro (Pro tier)
            "gemini-2.5-flash",              # Gemini 2.5 Flash (fast, balanced)
            "gemini-2.5-flash-lite",         # Gemini 2.5 Flash Lite (cheapest)
        ],
        "default_model": "gemini-3.5-flash",
        "supports_streaming": True,
        "key_url": "https://aistudio.google.com/apikey",
        "key_prefix": "",
        "pricing": {
            "gemini-3.5-flash":   {"input": 0.35,  "output": 1.40},
            "gemini-2.5-pro":     {"input": 1.25,  "output": 5.00},
            "gemini-2.5-flash":   {"input": 0.30,  "output": 1.20},
            "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
        },
    },
    "deepseek": {
        "display": "DeepSeek (OpenAI-compatible)",
        "models": [
            "deepseek-chat",                  # DeepSeek-V3
            "deepseek-reasoner",              # DeepSeek-R1 (reasoning)
        ],
        "default_model": "deepseek-chat",
        "supports_streaming": True,
        "key_url": "https://platform.deepseek.com/api_keys",
        "key_prefix": "sk-",
        "pricing": {
            "deepseek-chat":      {"input": 0.27, "output": 1.10},
            "deepseek-reasoner":  {"input": 0.55, "output": 2.19},
        },
        "base_url": "https://api.deepseek.com",
    },
}


@dataclass
class UsageInfo:
    """Token usage + estimated cost."""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    elapsed_sec: float = 0.0
    model: str = ""
    provider: str = ""

    truncated: bool = False     # True when finish_reason == max_tokens / length

    def __str__(self):
        trunc = " [TRUNCATED]" if self.truncated else ""
        return (
            f"[{self.provider}/{self.model}]  "
            f"In: {self.input_tokens:,}  Out: {self.output_tokens:,}  "
            f"${self.cost_usd:.4f}  {self.elapsed_sec:.1f}s{trunc}"
        )

    def to_dict(self):
        return {
            "provider": self.provider,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 4),
            "elapsed_sec": round(self.elapsed_sec, 2),
            "truncated": self.truncated,
        }


# =========================================================================
# Retry helpers — transient API error recovery
# =========================================================================

_RETRY_CODES: frozenset = frozenset({429, 503, 529})  # 529 = Anthropic overloaded
_RETRY_PHRASES: tuple = (
    "rate limit",
    "quota exceeded",
    "too many requests",
    "service unavailable",
    "overloaded",
    "resource_exhausted",
    "temporarily unavailable",
    "high demand",
)
_RETRY_MAX: int = 3
_RETRY_BASE_DELAY: float = 2.0  # seconds; doubles per attempt: 2 s → 4 s → 8 s


def _is_retryable(exc: Exception) -> bool:
    """Return True for transient API errors worth retrying (4xx rate-limit, 5xx unavailable)."""
    for attr in ("status_code", "status", "code"):
        if getattr(exc, attr, None) in _RETRY_CODES:
            return True
    msg = str(exc).lower()
    return any(phrase in msg for phrase in _RETRY_PHRASES)


def _with_retry(fn, max_retries: int = _RETRY_MAX, base_delay: float = _RETRY_BASE_DELAY):
    """Call fn(), retrying on transient errors with exponential back-off.

    Schedule (default): 2 s → 4 s → 8 s.
    Non-retryable errors (auth, bad request, etc.) raise immediately on the first attempt.
    """
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt == max_retries or not _is_retryable(exc):
                raise
            time.sleep(base_delay * (2 ** attempt))


# =========================================================================
# AIClient — Unified Interface
# =========================================================================

class AIClient:
    """Multi-provider AI client."""

    def __init__(self, provider: str, api_key: str, model: Optional[str] = None):
        if provider not in PROVIDER_CATALOG:
            raise ValueError(f"Unknown provider: {provider}. Valid: {list(PROVIDER_CATALOG.keys())}")

        self.provider = provider
        self.api_key = api_key
        self.model = model or PROVIDER_CATALOG[provider]["default_model"]
        self.catalog = PROVIDER_CATALOG[provider]

        if not api_key:
            raise ValueError(f"API key is empty. Key required for {self.catalog['display']}: {self.catalog['key_url']}")

        # Init client per provider (lazy import)
        self._client = None

    def _lazy_init(self):
        """Import the provider SDK + create the client on first use."""
        if self._client is not None:
            return

        if self.provider == "anthropic":
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package missing. pip install anthropic")

        elif self.provider == "openai":
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package missing. pip install openai")

        elif self.provider == "deepseek":
            try:
                import openai
                self._client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url=self.catalog["base_url"],
                )
            except ImportError:
                raise ImportError("openai package missing (deepseek uses OpenAI-compatible). pip install openai")

        elif self.provider == "google":
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                try:
                    # Fallback: legacy package
                    import google.generativeai as genai_old
                    genai_old.configure(api_key=self.api_key)
                    self._client = genai_old
                except ImportError:
                    raise ImportError("google-genai or google-generativeai package missing. pip install google-genai")

    # Provider OUTPUT ceilings (API hard caps, not preferences). A workflow
    # step may ASK for more; the request is clamped here so the provider does
    # not reject the call — and the truncation warning downstream tells the
    # user which provider ran out of window. (Blind field test: a ~190-row
    # IO table needs >8k output tokens — DeepSeek cannot deliver that, the
    # deterministic RD01 autocomplete covers the gap instead.)
    _PROVIDER_MAX_OUTPUT = {
        "anthropic": 64000,
        "google": 65536,
        "openai": 16384,
        "deepseek": 8192,
    }

    # ---------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------
    def chat(
        self,
        system: str,
        user: str,
        max_tokens: int = 4096,
        on_chunk: Optional[Callable[[str], None]] = None,
        temperature: float = 0.3,
    ) -> tuple[str, UsageInfo]:
        """Unified chat call.

        Args:
            system: System prompt
            user: User message
            max_tokens: Max output token count (clamped to the provider's cap)
            on_chunk: Callback called on each token chunk during streaming
            temperature: 0.0-1.0 — creativity

        Returns:
            (response_text, UsageInfo)
        """
        self._lazy_init()
        t0 = time.time()
        _cap = self._PROVIDER_MAX_OUTPUT.get(self.provider)
        if _cap and max_tokens > _cap:
            max_tokens = _cap

        if self.provider == "anthropic":
            text, usage = self._chat_anthropic(system, user, max_tokens, on_chunk, temperature)
        elif self.provider == "openai":
            text, usage = self._chat_openai(system, user, max_tokens, on_chunk, temperature)
        elif self.provider == "deepseek":
            text, usage = self._chat_openai(system, user, max_tokens, on_chunk, temperature)
        elif self.provider == "google":
            text, usage = self._chat_google(system, user, max_tokens, on_chunk, temperature)
        else:
            raise ValueError(f"Provider implementation missing: {self.provider}")

        usage.elapsed_sec = time.time() - t0
        usage.model = self.model
        usage.provider = self.provider
        usage.cost_usd = self._calculate_cost(usage)
        return text, usage

    def _calculate_cost(self, usage: UsageInfo) -> float:
        """Compute cost from token counts."""
        pricing = self.catalog.get("pricing", {}).get(self.model)
        if not pricing:
            return 0.0
        return (
            usage.input_tokens / 1_000_000 * pricing["input"] +
            usage.output_tokens / 1_000_000 * pricing["output"]
        )

    # ---------------------------------------------------------------
    # Anthropic
    # ---------------------------------------------------------------
    def _chat_anthropic(self, system, user, max_tokens, on_chunk, temperature):
        usage = UsageInfo()
        full_text = ""

        if on_chunk:
            # Streaming — retry only if no chunks have been emitted yet
            # (retrying after partial output would send duplicates to the caller)
            for _attempt in range(_RETRY_MAX + 1):
                _chunks_started = False
                try:
                    with self._client.messages.stream(
                        model=self.model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        system=system,
                        messages=[{"role": "user", "content": user}],
                    ) as stream:
                        for text_chunk in stream.text_stream:
                            _chunks_started = True
                            full_text += text_chunk
                            on_chunk(text_chunk)
                        final = stream.get_final_message()
                        usage.input_tokens = final.usage.input_tokens
                        usage.output_tokens = final.usage.output_tokens
                        if final.stop_reason == "max_tokens":
                            usage.truncated = True
                    break
                except Exception as _exc:
                    if _attempt == _RETRY_MAX or not _is_retryable(_exc) or _chunks_started:
                        raise
                    full_text = ""
                    time.sleep(_RETRY_BASE_DELAY * (2 ** _attempt))
        else:
            # Non-streaming — full retry
            def _do_call():
                return self._client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
            response = _with_retry(_do_call)
            full_text = response.content[0].text
            usage.input_tokens = response.usage.input_tokens
            usage.output_tokens = response.usage.output_tokens
            if response.stop_reason == "max_tokens":
                usage.truncated = True

        return full_text, usage

    # ---------------------------------------------------------------
    # OpenAI / DeepSeek (compatible)
    # ---------------------------------------------------------------
    def _chat_openai(self, system, user, max_tokens, on_chunk, temperature):
        usage = UsageInfo()
        full_text = ""

        # o1 models do not support a system prompt — merge into user
        is_o1 = self.model.startswith("o1")
        messages = (
            [{"role": "user", "content": f"{system}\n\n{user}"}]
            if is_o1
            else [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )

        kwargs = {"model": self.model, "messages": messages}
        if is_o1:
            kwargs["max_completion_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = max_tokens
            kwargs["temperature"] = temperature

        if on_chunk and not is_o1:
            # Streaming — retry only before first chunk
            kwargs["stream"] = True
            kwargs["stream_options"] = {"include_usage": True}
            for _attempt in range(_RETRY_MAX + 1):
                _chunks_started = False
                try:
                    stream = self._client.chat.completions.create(**kwargs)
                    for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            text_chunk = chunk.choices[0].delta.content
                            _chunks_started = True
                            full_text += text_chunk
                            on_chunk(text_chunk)
                        if hasattr(chunk, "usage") and chunk.usage:
                            usage.input_tokens = chunk.usage.prompt_tokens
                            usage.output_tokens = chunk.usage.completion_tokens
                        if chunk.choices and chunk.choices[0].finish_reason == "length":
                            usage.truncated = True
                    break
                except Exception as _exc:
                    if _attempt == _RETRY_MAX or not _is_retryable(_exc) or _chunks_started:
                        raise
                    full_text = ""
                    time.sleep(_RETRY_BASE_DELAY * (2 ** _attempt))
        else:
            # Non-streaming (including o1)
            def _do_call():
                return self._client.chat.completions.create(**kwargs)
            response = _with_retry(_do_call)
            full_text = response.choices[0].message.content
            usage.input_tokens = response.usage.prompt_tokens
            usage.output_tokens = response.usage.completion_tokens
            if response.choices[0].finish_reason == "length":
                usage.truncated = True

        return full_text, usage

    # ---------------------------------------------------------------
    # Google Gemini
    # ---------------------------------------------------------------
    def _chat_google(self, system, user, max_tokens, on_chunk, temperature):
        usage = UsageInfo()
        full_text = ""

        # New google-genai package
        if hasattr(self._client, "models"):
            from google.genai import types

            config = types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                temperature=temperature,
            )

            if on_chunk:
                # Streaming — retry only before first chunk
                for _attempt in range(_RETRY_MAX + 1):
                    _chunks_started = False
                    try:
                        stream = self._client.models.generate_content_stream(
                            model=self.model,
                            contents=user,
                            config=config,
                        )
                        for chunk in stream:
                            if chunk.text:
                                _chunks_started = True
                                full_text += chunk.text
                                on_chunk(chunk.text)
                            if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                                usage.input_tokens = chunk.usage_metadata.prompt_token_count or 0
                                usage.output_tokens = chunk.usage_metadata.candidates_token_count or 0
                            if (hasattr(chunk, "candidates") and chunk.candidates
                                    and hasattr(chunk.candidates[0], "finish_reason")):
                                fr_val = getattr(chunk.candidates[0].finish_reason, "value",
                                                 chunk.candidates[0].finish_reason)
                                if fr_val == 2:  # FinishReason.MAX_TOKENS == 2
                                    usage.truncated = True
                        break
                    except Exception as _exc:
                        if _attempt == _RETRY_MAX or not _is_retryable(_exc) or _chunks_started:
                            raise
                        full_text = ""
                        time.sleep(_RETRY_BASE_DELAY * (2 ** _attempt))
            else:
                # Non-streaming — full retry
                def _do_call():
                    return self._client.models.generate_content(
                        model=self.model,
                        contents=user,
                        config=config,
                    )
                response = _with_retry(_do_call)
                # response.text raises ValueError when finish_reason != STOP
                # (e.g. MAX_TOKENS). Extract safely from candidates instead.
                try:
                    full_text = response.text or ""
                except (ValueError, AttributeError):
                    try:
                        parts = response.candidates[0].content.parts
                        full_text = "".join(p.text for p in parts if getattr(p, "text", None))
                    except Exception:
                        full_text = ""
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    usage.input_tokens = response.usage_metadata.prompt_token_count or 0
                    usage.output_tokens = response.usage_metadata.candidates_token_count or 0
                if (hasattr(response, "candidates") and response.candidates
                        and hasattr(response.candidates[0], "finish_reason")):
                    fr_val = getattr(response.candidates[0].finish_reason, "value",
                                     response.candidates[0].finish_reason)
                    if fr_val == 2:  # FinishReason.MAX_TOKENS == 2
                        usage.truncated = True
        else:
            # Legacy google-generativeai package (fallback)
            model = self._client.GenerativeModel(
                model_name=self.model,
                system_instruction=system,
            )
            config = {"max_output_tokens": max_tokens, "temperature": temperature}
            if on_chunk:
                for _attempt in range(_RETRY_MAX + 1):
                    _chunks_started = False
                    try:
                        stream = model.generate_content(user, generation_config=config, stream=True)
                        for chunk in stream:
                            if chunk.text:
                                _chunks_started = True
                                full_text += chunk.text
                                on_chunk(chunk.text)
                        if hasattr(stream, "usage_metadata"):
                            usage.input_tokens = stream.usage_metadata.prompt_token_count
                            usage.output_tokens = stream.usage_metadata.candidates_token_count
                        break
                    except Exception as _exc:
                        if _attempt == _RETRY_MAX or not _is_retryable(_exc) or _chunks_started:
                            raise
                        full_text = ""
                        time.sleep(_RETRY_BASE_DELAY * (2 ** _attempt))
            else:
                def _do_call_legacy():
                    return model.generate_content(user, generation_config=config)
                response = _with_retry(_do_call_legacy)
                full_text = response.text
                if hasattr(response, "usage_metadata"):
                    usage.input_tokens = response.usage_metadata.prompt_token_count
                    usage.output_tokens = response.usage_metadata.candidates_token_count

        return full_text, usage


# =========================================================================
# Helpers
# =========================================================================

    def chat_with_files(
        self,
        system: str,
        user: str,
        files: list,
        max_tokens: int = 8192,
        temperature: float = 0.3,
    ) -> tuple[str, UsageInfo]:
        """Multimodal chat: send local files (PDF, PNG, JPG, GIF) alongside text.

        Only supported for provider='google' (Gemini Vision API).
        Each file is uploaded to the Google Files API, used in the request,
        then immediately deleted to protect privacy.

        Args:
            system:      System prompt.
            user:        Text message accompanying the files.
            files:       List of pathlib.Path objects (PDF / image files).
            max_tokens:  Max output tokens.
            temperature: Creativity (0.0–1.0).

        Returns:
            (response_text, UsageInfo)

        Raises:
            NotImplementedError: If provider != 'google'.
            ImportError:         If google-genai package is not installed.
        """
        if self.provider != "google":
            raise NotImplementedError(
                f"chat_with_files() is only supported for provider='google'. "
                f"Current provider: '{self.provider}'"
            )
        self._lazy_init()
        t0 = __import__("time").time()
        text, usage = self._chat_google_with_files(system, user, files, max_tokens, temperature)
        usage.elapsed_sec = __import__("time").time() - t0
        usage.model    = self.model
        usage.provider = self.provider
        usage.cost_usd = self._calculate_cost(usage)
        return text, usage

    def _chat_google_with_files(self, system, user, files, max_tokens, temperature):
        usage    = UsageInfo()
        full_text = ""
        uploaded: list = []

        # Determine MIME type from extension
        _MIME: dict[str, str] = {
            ".pdf":  "application/pdf",
            ".png":  "image/png",
            ".jpg":  "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif":  "image/gif",
            ".webp": "image/webp",
        }

        try:
            if hasattr(self._client, "models"):
                # New google-genai SDK
                from google.genai import types  # type: ignore

                for fp in files:
                    from pathlib import Path as _Path
                    fp = _Path(fp)
                    mime = _MIME.get(fp.suffix.lower(), "application/octet-stream")
                    ufile = self._client.files.upload(
                        path=str(fp),
                        config=types.UploadFileConfig(mime_type=mime, display_name=fp.name),
                    )
                    uploaded.append(ufile)

                parts = [types.Part.from_uri(file_uri=u.uri, mime_type=u.mime_type) for u in uploaded]
                parts.append(types.Part.from_text(text=user))

                config = types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                )
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=parts,
                    config=config,
                )
                try:
                    full_text = response.text or ""
                except (ValueError, AttributeError):
                    try:
                        parts_out = response.candidates[0].content.parts
                        full_text = "".join(p.text for p in parts_out if getattr(p, "text", None))
                    except Exception:
                        full_text = ""
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    usage.input_tokens  = response.usage_metadata.prompt_token_count or 0
                    usage.output_tokens = response.usage_metadata.candidates_token_count or 0
                # S-5: multimodal path must report truncation like chat() does —
                # OCR of long listings silently lost trailing pages otherwise.
                if (hasattr(response, "candidates") and response.candidates
                        and hasattr(response.candidates[0], "finish_reason")):
                    fr_val = getattr(response.candidates[0].finish_reason, "value",
                                     response.candidates[0].finish_reason)
                    if fr_val == 2:  # FinishReason.MAX_TOKENS == 2
                        usage.truncated = True
            else:
                # Legacy google-generativeai SDK — inline base64
                from pathlib import Path as _Path
                import base64
                model = self._client.GenerativeModel(
                    model_name=self.model,
                    system_instruction=system,
                )
                content = []
                for fp in files:
                    fp = _Path(fp)
                    mime = _MIME.get(fp.suffix.lower(), "application/octet-stream")
                    data = base64.b64encode(fp.read_bytes()).decode()
                    content.append({"mime_type": mime, "data": data})
                content.append(user)
                cfg = {"max_output_tokens": max_tokens, "temperature": temperature}
                response = model.generate_content(content, generation_config=cfg)
                full_text = response.text or ""
                if hasattr(response, "usage_metadata"):
                    usage.input_tokens  = response.usage_metadata.prompt_token_count or 0
                    usage.output_tokens = response.usage_metadata.candidates_token_count or 0
                if (hasattr(response, "candidates") and response.candidates
                        and hasattr(response.candidates[0], "finish_reason")):
                    fr_val = getattr(response.candidates[0].finish_reason, "value",
                                     response.candidates[0].finish_reason)
                    if fr_val == 2:  # FinishReason.MAX_TOKENS == 2
                        usage.truncated = True
        finally:
            # Delete uploaded files from Google servers immediately (privacy)
            for ufile in uploaded:
                try:
                    self._client.files.delete(name=ufile.name)
                except Exception:
                    pass

        return full_text, usage


def list_providers() -> list[str]:
    return list(PROVIDER_CATALOG.keys())


def list_models(provider: str) -> list[str]:
    return PROVIDER_CATALOG.get(provider, {}).get("models", [])


def get_provider_info(provider: str) -> dict:
    return PROVIDER_CATALOG.get(provider, {})


def test_api_key(provider: str, api_key: str, model: Optional[str] = None) -> tuple[bool, str]:
    """Test an API key — a simple 'hello' call."""
    try:
        client = AIClient(provider=provider, api_key=api_key, model=model)
        response, usage = client.chat(
            system="You are a helpful assistant.",
            user="Reply with exactly one word: hello",
            max_tokens=64,
        )
        return True, f"OK: '{response.strip()}' ({usage})"
    except Exception as e:
        return False, f"Error: {type(e).__name__}: {e}"


if __name__ == "__main__":
    # Self-test
    print("=== AI CLIENT TEST ===\n")
    for provider in list_providers():
        info = get_provider_info(provider)
        print(f"  {provider}: {info['display']}")
        print(f"    Models: {len(info['models'])} items")
        print(f"    Default: {info['default_model']}")
        print(f"    Key URL: {info['key_url']}\n")
    print("OK — AIClient ready")
