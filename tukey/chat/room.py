"""Chatroom logic: create rooms, manage models, fan-out prompts."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from tukey.config import ConfigManager
from tukey.providers.litellm_provider import LiteLLMProvider
from tukey.providers.base import LLMResponse, StreamChunk
from tukey.storage import Storage


class ChatRoom:
    def __init__(self, storage: Storage, config: ConfigManager, room_id: str | None = None):
        self.storage = storage
        self.config = config
        self.room_id = room_id or str(uuid.uuid4())

    def create(self, name: str, models: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        resolved_models = []
        for m in (models or []):
            resolved_models.append({
                "id": m.get("id", str(uuid.uuid4())),
                "provider_id": m["provider_id"],
                "model_id": m["model_id"],
                "display_name": m.get("display_name", m["model_id"]),
                "system_prompt": m.get("system_prompt", ""),
                "temperature": m.get("temperature", 1.0),
                "max_tokens": m.get("max_tokens"),
                "top_p": m.get("top_p"),
                "extra_params": m.get("extra_params", {}),
            })
        meta = {
            "id": self.room_id,
            "name": name,
            "created_at": now,
            "updated_at": now,
            "models": resolved_models,
        }
        self.storage.write_room_meta(self.room_id, meta)
        return meta

    def get_meta(self) -> dict[str, Any]:
        return self.storage.read_room_meta(self.room_id)

    def update_meta(self, updates: dict[str, Any]) -> dict[str, Any]:
        meta = self.get_meta()
        meta.update(updates)
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.storage.write_room_meta(self.room_id, meta)
        return meta

    def get_messages(self) -> list[dict[str, Any]]:
        return self.storage.read_messages(self.room_id)

    def _build_provider(self, provider_id: str) -> LiteLLMProvider:
        prov = self.config.get_provider(provider_id)
        if not prov:
            raise ValueError(f"Provider {provider_id} not found")
        return LiteLLMProvider(api_key=prov.get("api_key"), base_url=prov.get("base_url"))

    def _build_messages_for_model(self, model_cfg: dict, user_content: str) -> list[dict]:
        msgs: list[dict] = []
        if model_cfg.get("system_prompt"):
            msgs.append({"role": "system", "content": model_cfg["system_prompt"]})
        history = self.get_messages()
        for turn in history:
            msgs.append({"role": "user", "content": turn["content"]})
            for resp in turn.get("responses", []):
                if resp["model_id"] == model_cfg["id"]:
                    msgs.append({"role": "assistant", "content": resp["content"]})
        msgs.append({"role": "user", "content": user_content})
        return msgs

    async def send_message(self, content: str) -> dict[str, Any]:
        meta = self.get_meta()
        models = meta.get("models", [])
        turn_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        async def call_model(model_cfg: dict) -> dict:
            provider = self._build_provider(model_cfg["provider_id"])
            msgs = self._build_messages_for_model(model_cfg, content)
            kwargs: dict[str, Any] = {}
            if model_cfg.get("temperature") is not None:
                kwargs["temperature"] = model_cfg["temperature"]
            if model_cfg.get("max_tokens") is not None:
                kwargs["max_tokens"] = model_cfg["max_tokens"]
            if model_cfg.get("top_p") is not None:
                kwargs["top_p"] = model_cfg["top_p"]
            if model_cfg.get("extra_params"):
                kwargs["extra_params"] = model_cfg["extra_params"]
            resp = await provider.complete(msgs, model_cfg["model_id"], **kwargs)
            return {
                "model_id": model_cfg["id"],
                "content": resp.content,
                "tokens_in": resp.tokens_in,
                "tokens_out": resp.tokens_out,
                "cost": resp.cost,
                "duration_ms": resp.duration_ms,
                "tokens_per_sec": resp.tokens_per_sec,
            }

        responses = await asyncio.gather(
            *[call_model(m) for m in models], return_exceptions=True
        )
        resolved = []
        for i, r in enumerate(responses):
            if isinstance(r, Exception):
                resolved.append({
                    "model_id": models[i]["id"],
                    "content": str(r),
                    "error": True,
                })
            else:
                resolved.append(r)

        turn = {
            "id": turn_id,
            "role": "user",
            "content": content,
            "created_at": now,
            "responses": resolved,
        }
        self.storage.append_message(self.room_id, turn)
        return turn

    async def stream_message(
        self, content: str, model_cfg: dict
    ) -> AsyncIterator[StreamChunk]:
        provider = self._build_provider(model_cfg["provider_id"])
        msgs = self._build_messages_for_model(model_cfg, content)
        kwargs: dict[str, Any] = {}
        if model_cfg.get("temperature") is not None:
            kwargs["temperature"] = model_cfg["temperature"]
        if model_cfg.get("max_tokens") is not None:
            kwargs["max_tokens"] = model_cfg["max_tokens"]
        if model_cfg.get("top_p") is not None:
            kwargs["top_p"] = model_cfg["top_p"]
        async for chunk in provider.stream(msgs, model_cfg["model_id"], **kwargs):
            yield chunk
