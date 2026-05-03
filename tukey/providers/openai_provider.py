"""OpenAI-compatible provider: direct httpx calls to any OpenAI-format API."""

from __future__ import annotations

import base64
import json
import logging
import re
import time
from typing import Any, AsyncIterator

import httpx

from .base import ImageResponse, ImageResult, LLMResponse, StreamChunk, ToolCallInfo
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

    def _auth_headers(self) -> dict[str, str]:
        h = {}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    @staticmethod
    def _parse_data_url(data_url: str) -> tuple[bytes, str]:
        match = re.fullmatch(r"data:([^;,]+);base64,(.+)", data_url, flags=re.DOTALL)
        if not match:
            raise ValueError("Expected a base64 data URL")
        try:
            return base64.b64decode(match.group(2), validate=True), match.group(1)
        except Exception as exc:
            raise ValueError("Invalid base64 image data") from exc

    def _normalize_model(self, model: str) -> str:
        if self.strip_model_prefix and "/" in model:
            return model.split("/", 1)[1]
        return model

    @staticmethod
    def _uses_legacy_image_response_format(model: str) -> bool:
        """DALL-E image endpoints need response_format for base64; GPT Image does not."""
        return model.startswith("dall-e-")

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = resp.text.strip()
            if detail:
                raise RuntimeError(f"API {resp.status_code}: {detail[:1000]}") from exc
            raise

    def _build_payload(self, model: str, messages: list[dict], **extra: Any) -> dict:
        payload: dict[str, Any] = {"model": self._normalize_model(model), "messages": messages}
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
            self._raise_for_status(resp)
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

    async def generate_image(
        self, messages: list[dict], model: str, **kwargs: Any
    ) -> ImageResponse:
        if self.provider_type == "openrouter":
            return await self._generate_openrouter_image(messages, model, **kwargs)
        return await self._generate_native_image(messages, model, **kwargs)

    async def edit_image(
        self, messages: list[dict], model: str, **kwargs: Any
    ) -> ImageResponse:
        if self.provider_type == "openrouter":
            return await self._generate_openrouter_image(messages, model, **kwargs)
        return await self._edit_native_image(messages, model, **kwargs)

    async def _generate_openrouter_image(
        self, messages: list[dict], model: str, **kwargs: Any
    ) -> ImageResponse:
        extra_params = kwargs.get("extra_params") if isinstance(kwargs.get("extra_params"), dict) else {}
        payload: dict[str, Any] = {
            "model": self._normalize_model(model),
            "messages": messages,
            "modalities": extra_params.get("modalities", ["image", "text"]),
            "stream": False,
        }
        for key in ("temperature", "top_p", "max_tokens"):
            if kwargs.get(key) is not None:
                payload[key] = kwargs[key]
        for key, value in extra_params.items():
            if value is not None:
                payload[key] = value

        start = time.perf_counter()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
                timeout=300.0,
            )
            self._raise_for_status(resp)
            data = resp.json()
            duration_ms = (time.perf_counter() - start) * 1000
            return await self._openrouter_image_response(data, model, duration_ms, client)

    async def _generate_native_image(
        self, messages: list[dict], model: str, **kwargs: Any
    ) -> ImageResponse:
        if self._messages_have_images(messages):
            raise ValueError(
                "native image_generation does not support image inputs; use image_edit or OpenRouter multimodal image generation"
            )
        extra_params = kwargs.get("extra_params") if isinstance(kwargs.get("extra_params"), dict) else {}
        normalized_model = self._normalize_model(model)
        payload: dict[str, Any] = {
            "model": normalized_model,
            "prompt": self._messages_to_prompt(messages),
        }
        for key in (
            "size",
            "quality",
            "output_format",
            "output_compression",
            "moderation",
            "background",
            "user",
        ):
            if extra_params.get(key) is not None:
                payload[key] = extra_params[key]
        if self._uses_legacy_image_response_format(normalized_model):
            payload.setdefault("response_format", "b64_json")

        start = time.perf_counter()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/images/generations",
                json=payload,
                headers=self._headers(),
                timeout=300.0,
            )
            self._raise_for_status(resp)
            data = resp.json()
            duration_ms = (time.perf_counter() - start) * 1000
            return await self._native_image_response(
                data,
                model,
                duration_ms,
                client,
                output_format=payload.get("output_format", "png"),
            )

    async def _edit_native_image(
        self, messages: list[dict], model: str, **kwargs: Any
    ) -> ImageResponse:
        extra_params = kwargs.get("extra_params") if isinstance(kwargs.get("extra_params"), dict) else {}
        prompt = self._messages_to_prompt(messages)
        image_inputs = self._message_images(messages)
        if not image_inputs:
            raise ValueError("image_edit requires at least one image input block")

        data: dict[str, Any] = {
            "model": self._normalize_model(model),
            "prompt": prompt,
        }
        for key in ("size", "quality", "output_format", "background", "user"):
            if extra_params.get(key) is not None:
                data[key] = extra_params[key]
        if self._uses_legacy_image_response_format(data["model"]):
            data.setdefault("response_format", "b64_json")

        files = []
        for index, image in enumerate(image_inputs):
            filename = f"image-{index}.{self._extension_for_mime(image['mime_type'])}"
            files.append(("image", (filename, image["data"], image["mime_type"])))

        start = time.perf_counter()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/images/edits",
                data=data,
                files=files,
                headers=self._auth_headers(),
                timeout=300.0,
            )
            self._raise_for_status(resp)
            raw = resp.json()
            duration_ms = (time.perf_counter() - start) * 1000
            return await self._native_image_response(
                raw,
                model,
                duration_ms,
                client,
                output_format=data.get("output_format", "png"),
                source="openai_images_edits",
            )

    @staticmethod
    def _extension_for_mime(mime_type: str) -> str:
        return {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/webp": "webp",
            "image/gif": "gif",
        }.get(mime_type, "bin")

    @classmethod
    def _message_images(cls, messages: list[dict]) -> list[dict[str, Any]]:
        images: list[dict[str, Any]] = []
        for message in messages:
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "image_url":
                    continue
                url = (block.get("image_url") or {}).get("url")
                if not url:
                    continue
                data, mime_type = cls._parse_data_url(url)
                images.append({"data": data, "mime_type": mime_type})
        return images

    @classmethod
    def _messages_have_images(cls, messages: list[dict]) -> bool:
        for message in messages:
            content = message.get("content")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "image_url":
                        return True
        return False

    @staticmethod
    def _messages_to_prompt(messages: list[dict]) -> str:
        parts = []
        for message in messages:
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                parts.append(content.strip())
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = str(block.get("text", "")).strip()
                        if text:
                            parts.append(text)
        return "\n\n".join(parts)

    @classmethod
    async def _openrouter_image_response(
        cls,
        data: dict[str, Any],
        model: str,
        duration_ms: float,
        client: httpx.AsyncClient,
    ) -> ImageResponse:
        choices = data.get("choices") or []
        message = choices[0].get("message", {}) if choices else {}
        images = []
        for item in message.get("images") or []:
            image_url = item.get("image_url", {})
            url = image_url.get("url")
            if not url:
                continue
            image_bytes, mime_type = await cls._image_bytes_from_url(url, client)
            images.append(ImageResult(
                data=image_bytes,
                mime_type=mime_type,
                metadata={"source": "openrouter_chat_completions"},
            ))
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0) or 0
        tokens_out = usage.get("completion_tokens", 0) or 0
        return ImageResponse(
            images=images,
            content=message.get("content") or "",
            usage={
                "input_tokens": tokens_in,
                "output_tokens": tokens_out,
                **usage,
            },
            cost=None,
            duration_ms=round(duration_ms, 1),
            model=model,
            raw_response=data,
        )

    @classmethod
    async def _native_image_response(
        cls,
        data: dict[str, Any],
        model: str,
        duration_ms: float,
        client: httpx.AsyncClient,
        *,
        output_format: str = "png",
        source: str = "openai_images_generations",
    ) -> ImageResponse:
        images = []
        revised_prompts = []
        for item in data.get("data") or []:
            mime_type = f"image/{item.get('output_format', data.get('output_format', output_format))}"
            b64_json = item.get("b64_json")
            if b64_json:
                try:
                    image_bytes = base64.b64decode(b64_json, validate=True)
                except Exception as exc:
                    raise ValueError("Invalid base64 image data") from exc
            elif isinstance(item.get("url"), str):
                image_bytes, mime_type = await cls._image_bytes_from_url(item["url"], client)
            else:
                continue
            revised_prompt = item.get("revised_prompt")
            if revised_prompt:
                revised_prompts.append(revised_prompt)
            images.append(ImageResult(
                data=image_bytes,
                mime_type=mime_type,
                revised_prompt=revised_prompt,
                metadata={"source": source},
            ))
        return ImageResponse(
            images=images,
            content="\n\n".join(revised_prompts),
            usage=data.get("usage", {}),
            cost=None,
            duration_ms=round(duration_ms, 1),
            model=model,
            raw_response=data,
        )

    @classmethod
    async def _image_bytes_from_url(
        cls,
        url: str,
        client: httpx.AsyncClient,
    ) -> tuple[bytes, str]:
        if url.startswith("data:"):
            return cls._parse_data_url(url)
        if not url.startswith("https://"):
            raise ValueError("Image URL must be a base64 data URL or HTTPS URL")
        resp = await client.get(url, timeout=60.0)
        cls._raise_for_status(resp)
        mime_type = resp.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if not mime_type.startswith("image/"):
            raise ValueError(f"Hosted image URL returned non-image content type: {mime_type or 'unknown'}")
        return resp.content, mime_type

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
