"""LiteLLM-based provider: unified interface to OpenAI, Anthropic, Google, etc."""

from __future__ import annotations

import time
from typing import Any, AsyncIterator

import litellm

from .base import LLMResponse, StreamChunk

# Suppress litellm's noisy debug output for unmapped models
litellm.suppress_debug_info = True

_registered_models: set[str] = set()


def _ensure_model_registered(model: str) -> None:
    """Register unknown models so litellm doesn't reject them."""
    if model in _registered_models:
        return
    try:
        litellm.get_model_info(model)
    except Exception:
        # Extract the provider prefix (e.g. "openai" from "openai/claude-4.6-sonnet")
        provider = model.split("/")[0] if "/" in model else "openai"
        litellm.register_model({
            model: {
                "max_tokens": 16384,
                "max_input_tokens": 200000,
                "max_output_tokens": 16384,
                "input_cost_per_token": 0.0,
                "output_cost_per_token": 0.0,
                "litellm_provider": provider,
                "mode": "chat",
            }
        })
    _registered_models.add(model)


class LiteLLMProvider:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url

    def _build_kwargs(self, model: str, messages: list[dict], **extra: Any) -> dict:
        _ensure_model_registered(model)
        kwargs: dict[str, Any] = {"model": model, "messages": messages}
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.base_url:
            kwargs["api_base"] = self.base_url
        # Forward supported params
        for key in ("temperature", "max_tokens", "top_p", "stop", "stream",
                    "response_format", "tools", "tool_choice"):
            if key in extra and extra[key] is not None:
                kwargs[key] = extra[key]
        if "extra_params" in extra and isinstance(extra["extra_params"], dict):
            kwargs.update(extra["extra_params"])
        return kwargs

    async def complete(
        self, messages: list[dict], model: str, **kwargs: Any
    ) -> LLMResponse:
        call_kwargs = self._build_kwargs(model, messages, **kwargs)
        start = time.perf_counter()
        resp = await litellm.acompletion(**call_kwargs)
        duration_ms = (time.perf_counter() - start) * 1000

        content = resp.choices[0].message.content or ""
        usage = resp.usage or type("U", (), {"prompt_tokens": 0, "completion_tokens": 0})()
        tokens_in = usage.prompt_tokens
        tokens_out = usage.completion_tokens
        try:
            cost = litellm.completion_cost(completion_response=resp) or 0.0
        except Exception:
            cost = 0.0
        tps = (tokens_out / (duration_ms / 1000)) if duration_ms > 0 else 0.0

        return LLMResponse(
            content=content,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost,
            duration_ms=round(duration_ms, 1),
            tokens_per_sec=round(tps, 1),
            model=model,
            raw_response=resp.model_dump() if hasattr(resp, "model_dump") else {},
        )

    async def stream(
        self, messages: list[dict], model: str, **kwargs: Any
    ) -> AsyncIterator[StreamChunk]:
        call_kwargs = self._build_kwargs(model, messages, stream=True, **kwargs)
        start = time.perf_counter()
        chunks_text: list[str] = []
        tokens_in = 0
        tokens_out = 0

        resp = await litellm.acompletion(**call_kwargs)
        async for chunk in resp:
            delta = ""
            if chunk.choices and chunk.choices[0].delta.content:
                delta = chunk.choices[0].delta.content
                chunks_text.append(delta)

            if hasattr(chunk, "usage") and chunk.usage:
                tokens_in = getattr(chunk.usage, "prompt_tokens", 0) or 0
                tokens_out = getattr(chunk.usage, "completion_tokens", 0) or 0

            if chunk.choices and chunk.choices[0].finish_reason:
                duration_ms = (time.perf_counter() - start) * 1000
                full_content = "".join(chunks_text)
                if tokens_out == 0:
                    tokens_out = len(full_content) // 4  # rough estimate
                tps = (tokens_out / (duration_ms / 1000)) if duration_ms > 0 else 0.0
                yield StreamChunk(
                    delta=delta,
                    done=True,
                    response=LLMResponse(
                        content=full_content,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        cost=0.0,
                        duration_ms=round(duration_ms, 1),
                        tokens_per_sec=round(tps, 1),
                        model=model,
                    ),
                )
            elif delta:
                yield StreamChunk(delta=delta)
