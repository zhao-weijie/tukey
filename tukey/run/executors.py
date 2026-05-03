"""Executors for run-native task types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from tukey.providers.base import LLMResponse
from tukey.providers.openai_provider import OpenAICompatibleProvider


class TextProvider(Protocol):
    async def complete(
        self,
        messages: list[dict[str, Any]],
        model: str,
        **kwargs: Any,
    ) -> LLMResponse: ...


ProviderFactory = Callable[[dict[str, Any]], TextProvider]


def default_provider_factory(provider: dict[str, Any]) -> TextProvider:
    return OpenAICompatibleProvider(
        api_key=provider.get("api_key"),
        base_url=provider.get("base_url"),
        provider_type=provider.get("provider"),
        strip_model_prefix=provider.get("strip_model_prefix", False),
    )


def text_blocks_to_text(content: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for block in content:
        if block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "\n".join(part for part in parts if part)


def normalize_content_blocks(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, str):
        return [{"type": "text", "text": value}]
    if isinstance(value, list):
        normalized = []
        for item in value:
            if isinstance(item, str):
                normalized.append({"type": "text", "text": item})
            elif isinstance(item, dict):
                normalized.append(item)
            else:
                normalized.append({"type": "text", "text": str(item)})
        return normalized
    if isinstance(value, dict):
        return [value]
    return [{"type": "text", "text": str(value)}]


@dataclass
class TextCompletionExecutor:
    provider: TextProvider

    async def execute(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        slot_snapshot: dict[str, Any],
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {}
        for key in (
            "temperature",
            "max_tokens",
            "top_p",
            "extra_params",
            "response_format",
            "tools",
            "tool_choice",
        ):
            if slot_snapshot.get(key) is not None:
                kwargs[key] = slot_snapshot[key]
        return await self.provider.complete(messages, model, **kwargs)
