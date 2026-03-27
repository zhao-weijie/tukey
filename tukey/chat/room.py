"""Chatroom logic: create chatrooms, manage models, fan-out prompts."""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime, timezone
from importlib.metadata import version as pkg_version
from typing import Any, AsyncIterator

import json as json_mod
import tukey
from tukey.config import ConfigManager
from tukey.providers.openai_provider import OpenAICompatibleProvider
from tukey.providers.base import StreamChunk, ToolCallInfo, ToolResultInfo
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
                "mcp_server_ids": m.get("mcp_server_ids"),
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
            "httpx_version": pkg_version("httpx"),
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
    def _export_chat_data(
        storage: Storage,
        chatroom_id: str,
        chat_id: str,
        *,
        include_annotations: bool = True,
        turn_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build export dict for a single chat."""
        chat_meta = storage.read_chat_meta(chatroom_id, chat_id)
        if not chat_meta:
            raise ValueError(f"Chat {chat_id} not found")
        messages = storage.read_chat_messages(chatroom_id, chat_id)
        if turn_ids is not None:
            turn_set = set(turn_ids)
            messages = [m for m in messages if m.get("id") in turn_set]
        chat_data: dict[str, Any] = {
            "name": chat_meta.get("name"),
            "models_snapshot": chat_meta.get("models_snapshot", []),
            "providers_snapshot": chat_meta.get("providers_snapshot", {}),
            "runtime": chat_meta.get("runtime", {}),
            "created_at": chat_meta.get("created_at"),
            "messages": messages,
        }
        if include_annotations:
            annotations = storage.read_chat_annotations(chatroom_id, chat_id)
            if turn_ids is not None:
                turn_set = set(turn_ids)
                annotations = [
                    a for a in annotations
                    if a.get("target", {}).get("source", {}).get("message_id") in turn_set
                ]
            chat_data["annotations"] = annotations
        else:
            chat_data["annotations"] = []
        return chat_data

    @staticmethod
    def export_chatroom(
        storage: Storage,
        chatroom_id: str,
        *,
        include_annotations: bool = True,
    ) -> dict[str, Any]:
        meta = storage.read_chatroom_meta(chatroom_id)
        if not meta:
            raise ValueError(f"Chatroom {chatroom_id} not found")
        chats_export = []
        for cid in storage.list_chats(chatroom_id):
            try:
                chat_data = ChatRoom._export_chat_data(
                    storage, chatroom_id, cid,
                    include_annotations=include_annotations,
                )
                chats_export.append(chat_data)
            except ValueError:
                continue
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
    def export_chat(
        storage: Storage,
        chatroom_id: str,
        chat_id: str,
        *,
        include_annotations: bool = True,
        turn_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        meta = storage.read_chatroom_meta(chatroom_id)
        if not meta:
            raise ValueError(f"Chatroom {chatroom_id} not found")
        chat_data = ChatRoom._export_chat_data(
            storage, chatroom_id, chat_id,
            include_annotations=include_annotations,
            turn_ids=turn_ids,
        )
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
            "chats": [chat_data],
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

    def _build_provider(self, provider_id: str) -> OpenAICompatibleProvider:
        prov = self.config.get_provider(provider_id)
        if not prov:
            raise ValueError(f"Provider {provider_id} not found")
        return OpenAICompatibleProvider(
            api_key=prov.get("api_key"),
            base_url=prov.get("base_url"),
            provider_type=prov.get("provider"),
            strip_model_prefix=prov.get("strip_model_prefix", False),
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
                    # Build assistant message with content and tool calls
                    assistant_msg: dict[str, Any] = {"role": "assistant"}
                    if resp.get("content"):
                        assistant_msg["content"] = resp["content"]
                    # Include tool calls and tool results from previous interactions
                    tool_interactions = resp.get("tool_interactions", [])
                    if tool_interactions:
                        for interaction in tool_interactions:
                            tool_calls = interaction.get("tool_calls", [])
                            tool_results = interaction.get("tool_results", [])
                            if tool_calls:
                                assistant_msg["tool_calls"] = [
                                    {
                                        "id": tc["id"],
                                        "type": "function",
                                        "function": {"name": tc["name"], "arguments": tc["arguments"]},
                                    }
                                    for tc in tool_calls
                                ]
                            # Add tool result messages after the assistant message
                            for tr in tool_results:
                                msgs.append({
                                    "role": "tool",
                                    "tool_call_id": tr["tool_call_id"],
                                    "content": tr["result"],
                                })
                    msgs.append(assistant_msg)
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
            kwargs = self._extract_kwargs(model_cfg)
            if model_cfg.get("tools"):
                kwargs["tools"] = model_cfg["tools"]
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
            "response_indices": response_indices,
        }
        self.storage.append_chat_message(self.chatroom_id, chat_id, turn)
        return turn

    @staticmethod
    def _extract_kwargs(model_cfg: dict) -> dict[str, Any]:
        """Extract LLM kwargs from a model config dict."""
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
        if model_cfg.get("tool_choice") is not None:
            kwargs["tool_choice"] = model_cfg["tool_choice"]
        return kwargs

    async def _resolve_tools(
        self, model_cfg: dict, mcp_manager: Any | None,
    ) -> tuple[list[dict] | None, dict[str, str]]:
        """Merge MCP tools + raw tools. Returns (tools_list, tool_name->server_id routing)."""
        tools: list[dict] = []
        routing: dict[str, str] = {}

        # MCP server tools
        mcp_ids = model_cfg.get("mcp_server_ids") or []
        if mcp_ids and mcp_manager:
            mcp_tools = await mcp_manager.get_tools(mcp_ids, self.config)
            tools.extend(mcp_tools)
            routing = mcp_manager.get_tool_routing(mcp_ids)

        # Raw tools from model config
        if model_cfg.get("tools"):
            tools.extend(model_cfg["tools"])

        return (tools if tools else None, routing)

    async def stream_message(
        self, chat_id: str, content: str, model_cfg: dict,
        response_indices: dict[str, int] | None = None,
        mcp_manager: Any | None = None,
    ) -> AsyncIterator[StreamChunk]:
        provider = self._build_provider(model_cfg["provider_id"])
        msgs = self._build_messages_for_model(chat_id, model_cfg, content, response_indices)
        kwargs = self._extract_kwargs(model_cfg)

        # Resolve tools (MCP + raw)
        tools, tool_routing = await self._resolve_tools(model_cfg, mcp_manager)
        if tools:
            kwargs["tools"] = tools
            if "tool_choice" not in kwargs or kwargs["tool_choice"] is None:
                kwargs["tool_choice"] = "auto"

        MAX_ITERATIONS = 10
        for iteration in range(MAX_ITERATIONS):
            final_chunk: StreamChunk | None = None

            async for chunk in provider.stream(msgs, model_cfg["model_id"], **kwargs):
                if chunk.done:
                    final_chunk = chunk
                yield chunk

            # Check if the model made tool calls
            if not final_chunk or not final_chunk.tool_calls or not mcp_manager:
                break

            # Build assistant message with tool_calls for conversation history
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": tc.arguments},
                    }
                    for tc in final_chunk.tool_calls
                ],
            }
            if final_chunk.response and final_chunk.response.content:
                assistant_msg["content"] = final_chunk.response.content
            msgs.append(assistant_msg)

            # Execute each tool call
            for tc in final_chunk.tool_calls:
                server_id = tool_routing.get(tc.name)
                if server_id:
                    try:
                        result = await mcp_manager.call_tool(
                            server_id, tc.name,
                            json_mod.loads(tc.arguments) if tc.arguments else {},
                        )
                        yield StreamChunk(tool_result=ToolResultInfo(
                            tool_call_id=tc.id, name=tc.name, result=result,
                        ))
                    except Exception as e:
                        result = json_mod.dumps({"error": str(e)})
                        yield StreamChunk(tool_result=ToolResultInfo(
                            tool_call_id=tc.id, name=tc.name, result=result, error=True,
                        ))
                else:
                    result = json_mod.dumps({"error": f"Unknown tool: {tc.name}"})
                    yield StreamChunk(tool_result=ToolResultInfo(
                        tool_call_id=tc.id, name=tc.name, result=result, error=True,
                    ))

                msgs.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
