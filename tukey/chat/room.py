"""Chatroom logic: create chatrooms, manage models, fan-out prompts."""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime, timezone
from importlib.metadata import version as pkg_version
from typing import Any, AsyncIterator

import tukey
from tukey.config import ConfigManager
from tukey.providers.litellm_provider import LiteLLMProvider
from tukey.providers.base import StreamChunk
from tukey.storage import Storage


class ChatRoom:
    def __init__(self, storage: Storage, config: ConfigManager, chatroom_id: str | None = None):
        self.storage = storage
        self.config = config
        self.chatroom_id = chatroom_id or str(uuid.uuid4())

    # --- Chatroom CRUD ---

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
                "response_format": m.get("response_format"),
                "tools": m.get("tools"),
                "tool_choice": m.get("tool_choice"),
            })
        meta = {
            "id": self.chatroom_id,
            "name": name,
            "created_at": now,
            "updated_at": now,
            "models": resolved_models,
        }
        self.storage.write_chatroom_meta(self.chatroom_id, meta)
        return meta

    def get_meta(self) -> dict[str, Any]:
        return self.storage.read_chatroom_meta(self.chatroom_id)

    def update_meta(self, updates: dict[str, Any]) -> dict[str, Any]:
        meta = self.get_meta()
        meta.update(updates)
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.storage.write_chatroom_meta(self.chatroom_id, meta)
        return meta

    # --- Chat CRUD ---

    def create_chat(self, name: str | None = None) -> dict[str, Any]:
        chatroom_meta = self.get_meta()
        chat_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        existing = self.storage.list_chats(self.chatroom_id)
        chat_name = name or f"Chat {len(existing) + 1}"
        models = chatroom_meta.get("models", [])

        # Collect unique provider snapshots (strip api_key)
        providers_snapshot: dict[str, Any] = {}
        for m in models:
            pid = m.get("provider_id")
            if pid and pid not in providers_snapshot:
                prov = self.config.get_provider(pid)
                if prov:
                    providers_snapshot[pid] = {
                        "id": prov["id"],
                        "provider": prov.get("provider"),
                        "base_url": prov.get("base_url"),
                        "display_name": prov.get("display_name"),
                    }

        runtime = {
            "tukey_version": tukey.__version__,
            "litellm_version": pkg_version("litellm"),
            "python_version": sys.version,
        }

        chat_meta = {
            "id": chat_id,
            "name": chat_name,
            "models_snapshot": models,
            "providers_snapshot": providers_snapshot,
            "runtime": runtime,
            "created_at": now,
        }
        self.storage.write_chat_meta(self.chatroom_id, chat_id, chat_meta)
        return chat_meta

    def get_chat_meta(self, chat_id: str) -> dict[str, Any]:
        return self.storage.read_chat_meta(self.chatroom_id, chat_id)

    def list_chats(self) -> list[dict[str, Any]]:
        chats = []
        for cid in self.storage.list_chats(self.chatroom_id):
            meta = self.storage.read_chat_meta(self.chatroom_id, cid)
            if meta:
                chats.append(meta)
        return chats

    def get_messages(self, chat_id: str) -> list[dict[str, Any]]:
        return self.storage.read_chat_messages(self.chatroom_id, chat_id)

    # --- Reproducibility ---

    def get_manifest(self, chat_id: str) -> dict[str, Any]:
        """Build a reproducibility manifest from existing chat data."""
        chatroom_meta = self.get_meta()
        chat_meta = self.get_chat_meta(chat_id)
        messages = self.get_messages(chat_id)

        user_turns = []
        for msg in messages:
            turn: dict[str, Any] = {"content": msg["content"]}
            turn["responses"] = [
                {
                    "model_id": r["model_id"],
                    "tokens_in": r.get("tokens_in"),
                    "tokens_out": r.get("tokens_out"),
                    "cost": r.get("cost"),
                    "duration_ms": r.get("duration_ms"),
                    "error": r.get("error", False),
                }
                for r in msg.get("responses", [])
            ]
            user_turns.append(turn)

        return {
            "chatroom": {
                "name": chatroom_meta["name"],
                "models": chatroom_meta.get("models", []),
            },
            "chat": {
                "id": chat_id,
                "name": chat_meta.get("name"),
                "created_at": chat_meta.get("created_at"),
                "models_snapshot": chat_meta.get("models_snapshot", []),
                "providers_snapshot": chat_meta.get("providers_snapshot", {}),
                "runtime": chat_meta.get("runtime", {}),
            },
            "turns": user_turns,
        }

    async def replay_chat(self, source_chat_id: str, name: str | None = None) -> dict[str, Any]:
        """Replay a chat: create new chat, re-send all user turns, return new chat + messages."""
        source_messages = self.get_messages(source_chat_id)
        replay_name = name or "Replay"
        new_chat = self.create_chat(replay_name)
        new_chat_id = new_chat["id"]

        all_turns = []
        for msg in source_messages:
            turn = await self.send_message(new_chat_id, msg["content"])
            all_turns.append(turn)

        return {"chat": new_chat, "turns": all_turns}

    # --- Export / Import ---

    @staticmethod
    def export_chatroom(storage: Storage, chatroom_id: str) -> dict[str, Any]:
        meta = storage.read_chatroom_meta(chatroom_id)
        if not meta:
            raise ValueError(f"Chatroom {chatroom_id} not found")
        chats_export = []
        for cid in storage.list_chats(chatroom_id):
            chat_meta = storage.read_chat_meta(chatroom_id, cid)
            if not chat_meta:
                continue
            messages = storage.read_chat_messages(chatroom_id, cid)
            annotations = storage.read_chat_annotations(chatroom_id, cid)
            chat_data = {
                "name": chat_meta.get("name"),
                "models_snapshot": chat_meta.get("models_snapshot", []),
                "providers_snapshot": chat_meta.get("providers_snapshot", {}),
                "runtime": chat_meta.get("runtime", {}),
                "created_at": chat_meta.get("created_at"),
                "messages": messages,
                "annotations": annotations,
            }
            chats_export.append(chat_data)
        return {
            "tukey_export": {
                "version": 1,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "tukey_version": tukey.__version__,
            },
            "chatroom": {
                "name": meta["name"],
                "models": meta.get("models", []),
                "created_at": meta.get("created_at"),
                "updated_at": meta.get("updated_at"),
            },
            "chats": chats_export,
        }

    @staticmethod
    def import_chatroom(
        storage: Storage, config: ConfigManager, data: dict[str, Any]
    ) -> dict[str, Any]:
        header = data.get("tukey_export")
        if not header or header.get("version") != 1:
            raise ValueError("Invalid or unsupported export format")
        cr_data = data["chatroom"]
        room = ChatRoom(storage, config)
        room_meta = room.create(
            name=cr_data["name"],
            models=cr_data.get("models", []),
        )
        for chat_data in data.get("chats", []):
            chat_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            chat_meta = {
                "id": chat_id,
                "name": chat_data.get("name", "Imported Chat"),
                "models_snapshot": chat_data.get("models_snapshot", []),
                "providers_snapshot": chat_data.get("providers_snapshot", {}),
                "runtime": chat_data.get("runtime", {}),
                "created_at": chat_data.get("created_at", now),
            }
            storage.write_chat_meta(room.chatroom_id, chat_id, chat_meta)
            for msg in chat_data.get("messages", []):
                new_msg = {**msg, "id": str(uuid.uuid4())}
                storage.append_chat_message(room.chatroom_id, chat_id, new_msg)
            for ann in chat_data.get("annotations", []):
                new_ann = {**ann, "id": str(uuid.uuid4())}
                storage.append_chat_annotation(room.chatroom_id, chat_id, new_ann)
        return room_meta

    # --- Provider ---

    def _build_provider(self, provider_id: str) -> LiteLLMProvider:
        prov = self.config.get_provider(provider_id)
        if not prov:
            raise ValueError(f"Provider {provider_id} not found")
        return LiteLLMProvider(
            api_key=prov.get("api_key"),
            base_url=prov.get("base_url"),
            provider_type=prov.get("provider"),
        )

    def _build_messages_for_model(
        self, chat_id: str, model_cfg: dict, user_content: str,
        response_indices: dict[str, int] | None = None,
    ) -> list[dict]:
        msgs: list[dict] = []
        if model_cfg.get("system_prompt"):
            msgs.append({"role": "system", "content": model_cfg["system_prompt"]})
        history = self.get_messages(chat_id)
        for turn in history:
            msgs.append({"role": "user", "content": turn["content"]})
            target_idx = (response_indices or {}).get(turn["id"], 0)
            for resp in turn.get("responses", []):
                if resp["model_id"] == model_cfg["id"] and resp.get("response_index", 0) == target_idx:
                    msgs.append({"role": "assistant", "content": resp["content"]})
        msgs.append({"role": "user", "content": user_content})
        return msgs

    # --- Messaging (uses chat's models_snapshot) ---

    async def send_message(
        self, chat_id: str, content: str, n: int = 1,
        response_indices: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        chat_meta = self.get_chat_meta(chat_id)
        models = chat_meta.get("models_snapshot", [])
        turn_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        n = min(max(n, 1), 9)

        async def call_model(model_cfg: dict, response_index: int) -> dict:
            provider = self._build_provider(model_cfg["provider_id"])
            msgs = self._build_messages_for_model(chat_id, model_cfg, content, response_indices)
            kwargs: dict[str, Any] = {}
            if model_cfg.get("temperature") is not None:
                kwargs["temperature"] = model_cfg["temperature"]
            if model_cfg.get("max_tokens") is not None:
                kwargs["max_tokens"] = model_cfg["max_tokens"]
            if model_cfg.get("top_p") is not None:
                kwargs["top_p"] = model_cfg["top_p"]
            if model_cfg.get("extra_params"):
                kwargs["extra_params"] = model_cfg["extra_params"]
            if model_cfg.get("response_format"):
                kwargs["response_format"] = model_cfg["response_format"]
            if model_cfg.get("tools"):
                kwargs["tools"] = model_cfg["tools"]
            if model_cfg.get("tool_choice") is not None:
                kwargs["tool_choice"] = model_cfg["tool_choice"]
            resp = await provider.complete(msgs, model_cfg["model_id"], **kwargs)
            return {
                "model_id": model_cfg["id"],
                "response_index": response_index,
                "content": resp.content,
                "tokens_in": resp.tokens_in,
                "tokens_out": resp.tokens_out,
                "cost": resp.cost,
                "duration_ms": resp.duration_ms,
                "tokens_per_sec": resp.tokens_per_sec,
            }

        tasks = []
        task_keys = []
        for m in models:
            for idx in range(n):
                tasks.append(call_model(m, idx))
                task_keys.append((m["id"], idx))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        resolved = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                model_id, resp_idx = task_keys[i]
                resolved.append({
                    "model_id": model_id,
                    "response_index": resp_idx,
                    "content": str(r),
                    "error": True,
                })
            else:
                resolved.append(r)

        resolved.sort(key=lambda r: (r["model_id"], r.get("response_index", 0)))

        turn = {
            "id": turn_id,
            "role": "user",
            "content": content,
            "created_at": now,
            "responses": resolved,
        }
        self.storage.append_chat_message(self.chatroom_id, chat_id, turn)
        return turn

    async def stream_message(
        self, chat_id: str, content: str, model_cfg: dict,
        response_indices: dict[str, int] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        provider = self._build_provider(model_cfg["provider_id"])
        msgs = self._build_messages_for_model(chat_id, model_cfg, content, response_indices)
        kwargs: dict[str, Any] = {}
        if model_cfg.get("temperature") is not None:
            kwargs["temperature"] = model_cfg["temperature"]
        if model_cfg.get("max_tokens") is not None:
            kwargs["max_tokens"] = model_cfg["max_tokens"]
        if model_cfg.get("top_p") is not None:
            kwargs["top_p"] = model_cfg["top_p"]
        if model_cfg.get("response_format"):
            kwargs["response_format"] = model_cfg["response_format"]
        if model_cfg.get("tools"):
            kwargs["tools"] = model_cfg["tools"]
        if model_cfg.get("tool_choice") is not None:
            kwargs["tool_choice"] = model_cfg["tool_choice"]
        async for chunk in provider.stream(msgs, model_cfg["model_id"], **kwargs):
            yield chunk
