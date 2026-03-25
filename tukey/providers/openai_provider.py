"""OpenAI-compatible provider: direct httpx calls to any OpenAI-format API."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, AsyncIterator

import httpx

from .base import LLMResponse, StreamChunk, ToolCallInfo
from . import model_registry

log = logging.getLogger(__name__)


class OpenAICompatibleProvider:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        provider_type: str | None = None,
        strip_model_prefix: bool = False,
    ):
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.provider_type = provider_type
        self.strip_model_prefix = strip_model_prefix

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _build_payload(self, model: str, messages: list[dict], **extra: Any) -> dict:
        if self.strip_model_prefix and "/" in model:
            model = model.split("/", 1)[1]
        payload: dict[str, Any] = {"model": model, "messages": messages}
        for key in ("temperature", "max_tokens", "top_p", "stop",
                    "response_format", "tools", "tool_choice"):
            if key in extra and extra[key] is not None:
                payload[key] = extra[key]
        if "extra_params" in extra and isinstance(extra["extra_params"], dict):
            payload.update(extra["extra_params"])
        if extra.get("stream"):
            payload["stream"] = True
            # stream_options is supported by OpenAI and OpenRouter; omit for other gateways
            if self.provider_type in ("openai", "openrouter"):
                payload["stream_options"] = {"include_usage": True}
        return payload

    async def complete(
        self, messages: list[dict], model: str, **kwargs: Any
    ) -> LLMResponse:
        payload = self._build_payload(model, messages, **kwargs)
        start = time.perf_counter()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
                timeout=300.0,
            )
            resp.raise_for_status()
            data = resp.json()

        duration_ms = (time.perf_counter() - start) * 1000

        content = data["choices"][0]["message"].get("content", "") or ""
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
        cost = model_registry.compute_cost(model, tokens_in, tokens_out)
        tps = (tokens_out / (duration_ms / 1000)) if duration_ms > 0 else 0.0

        return LLMResponse(
            content=content,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost,
            duration_ms=round(duration_ms, 1),
            tokens_per_sec=round(tps, 1),
            model=model,
            raw_response=data,
        )

    async def stream(
        self, messages: list[dict], model: str, **kwargs: Any
    ) -> AsyncIterator[StreamChunk]:
        payload = self._build_payload(model, messages, stream=True, **kwargs)
        log.info("stream request to %s/chat/completions model=%s strip_prefix=%s", self.base_url, payload["model"], self.strip_model_prefix)
        start = time.perf_counter()
        chunks_text: list[str] = []
        tokens_in = 0
        tokens_out = 0

        # Accumulate tool call deltas (keyed by index)
        tc_accum: dict[int, dict[str, str]] = {}  # {index: {id, name, arguments}}

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
                timeout=httpx.Timeout(300.0, connect=10.0),
            ) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    detail = body.decode(errors="replace")[:500]
                    log.error("API error %s: %s", resp.status_code, detail)
                    raise RuntimeError(f"API {resp.status_code}: {detail}")
                async for line in resp.aiter_lines():
                    # SSE spec: space after colon is optional
                    if line.startswith("data: "):
                        sse_data = line[6:]
                    elif line.startswith("data:"):
                        sse_data = line[5:]
                    else:
                        continue
                    if sse_data.strip() == "[DONE]":
                        break

                    chunk = json.loads(sse_data)
                    delta = ""
                    choices = chunk.get("choices", [])
                    choice = choices[0] if choices else {}
                    delta_obj = choice.get("delta", {})

                    # Accumulate content deltas
                    if delta_obj.get("content"):
                        delta = delta_obj["content"]
                        chunks_text.append(delta)

                    # Accumulate tool call deltas
                    for tc_delta in delta_obj.get("tool_calls", []):
                        idx = tc_delta.get("index", 0)
                        if idx not in tc_accum:
                            tc_accum[idx] = {"id": "", "name": "", "arguments": ""}
                        if tc_delta.get("id"):
                            tc_accum[idx]["id"] = tc_delta["id"]
                        fn = tc_delta.get("function", {})
                        if fn.get("name"):
                            tc_accum[idx]["name"] = fn["name"]
                        if fn.get("arguments"):
                            tc_accum[idx]["arguments"] += fn["arguments"]

                    usage = chunk.get("usage")
                    if usage:
                        tokens_in = usage.get("prompt_tokens", 0) or 0
                        tokens_out = usage.get("completion_tokens", 0) or 0

                    finish = choice.get("finish_reason") if choices else None
                    if finish:
                        duration_ms = (time.perf_counter() - start) * 1000
                        full_content = "".join(chunks_text)
                        if tokens_out == 0:
                            tokens_out = len(full_content) // 4
                        tps = (tokens_out / (duration_ms / 1000)) if duration_ms > 0 else 0.0
                        cost = model_registry.compute_cost(model, tokens_in, tokens_out)

                        # Build tool_calls list if any were accumulated
                        tool_calls = None
                        if tc_accum:
                            tool_calls = [
                                ToolCallInfo(
                                    id=tc["id"],
                                    name=tc["name"],
                                    arguments=tc["arguments"],
                                )
                                for tc in (tc_accum[i] for i in sorted(tc_accum))
                            ]

                        yield StreamChunk(
                            delta=delta,
                            done=True,
                            tool_calls=tool_calls,
                            response=LLMResponse(
                                content=full_content,
                                tokens_in=tokens_in,
                                tokens_out=tokens_out,
                                cost=cost,
                                duration_ms=round(duration_ms, 1),
                                tokens_per_sec=round(tps, 1),
                                model=model,
                            ),
                        )
                    elif delta:
                        yield StreamChunk(delta=delta)
