"""Executors for run-native task types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from tukey.providers.base import ImageResponse, LLMResponse
from tukey.providers.openai_provider import OpenAICompatibleProvider


class TextProvider(Protocol):
    async def complete(
        self,
        messages: list[dict[str, Any]],
        model: str,
        **kwargs: Any,
    ) -> LLMResponse: ...

    async def generate_image(
        self,
        messages: list[dict[str, Any]],
        model: str,
        **kwargs: Any,
    ) -> ImageResponse: ...

    async def edit_image(
        self,
        messages: list[dict[str, Any]],
        model: str,
        **kwargs: Any,
    ) -> ImageResponse: ...


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


def message_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "\n".join(part for part in parts if part)
    return ""


def messages_to_text(messages: list[dict[str, Any]]) -> str:
    return "\n".join(
        text
        for message in messages
        if message.get("role") != "system"
        for text in [message_content_to_text(message.get("content"))]
        if text
    )


def message_content_has_image(content: Any) -> bool:
    if not isinstance(content, list):
        return False
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "image_url":
            return True
    return False


def messages_have_image(messages: list[dict[str, Any]]) -> bool:
    return any(message_content_has_image(message.get("content")) for message in messages)


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


@dataclass
class ImageGenerationExecutor:
    provider: TextProvider

    async def execute(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        slot_snapshot: dict[str, Any],
    ) -> ImageResponse:
        if not messages_to_text(messages).strip():
            raise ValueError("image_generation requires at least one text input block")

        kwargs = self._image_kwargs(slot_snapshot)
        response = await self.provider.generate_image(messages, model, **kwargs)
        if not response.images:
            raise ValueError("image_generation provider returned no images")
        return response

    @staticmethod
    def _image_kwargs(slot_snapshot: dict[str, Any]) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        for key in ("temperature", "max_tokens", "top_p", "extra_params"):
            if slot_snapshot.get(key) is not None:
                kwargs[key] = slot_snapshot[key]
        return kwargs


@dataclass
class ImageEditExecutor:
    provider: TextProvider

    async def execute(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        slot_snapshot: dict[str, Any],
    ) -> ImageResponse:
        if not messages_to_text(messages).strip():
            raise ValueError("image_edit requires at least one text instruction block")
        if not messages_have_image(messages):
            raise ValueError("image_edit requires at least one image input block")

        kwargs = ImageGenerationExecutor._image_kwargs(slot_snapshot)
        response = await self.provider.edit_image(messages, model, **kwargs)
        if not response.images:
            raise ValueError("image_edit provider returned no images")
        return response
