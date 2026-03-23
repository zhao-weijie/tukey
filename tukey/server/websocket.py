"""WebSocket endpoint for streaming LLM responses."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from tukey.chat.room import ChatRoom
from tukey.config import ConfigManager
from tukey.storage import Storage

router = APIRouter()

_storage: Storage | None = None
_config: ConfigManager | None = None


def init(storage: Storage, config: ConfigManager) -> None:
    global _storage, _config
    _storage = storage
    _config = config


@router.websocket("/ws/chat/{chatroom_id}/{chat_id}")
async def chat_stream(ws: WebSocket, chatroom_id: str, chat_id: str):
    assert _storage and _config
    await ws.accept()
    ws_lock = asyncio.Lock()

    async def safe_send(msg: dict):
        async with ws_lock:
            await ws.send_json(msg)

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type", "send")

            if msg_type == "regenerate":
                await _handle_regenerate(ws, safe_send, chatroom_id, chat_id, data)
            else:
                await _handle_send(ws, safe_send, chatroom_id, chat_id, data)

    except WebSocketDisconnect:
        pass


async def _handle_send(
    ws: WebSocket, safe_send, chatroom_id: str, chat_id: str, data: dict
):
    content = data.get("content", "")
    if not content:
        return

    chat_meta = _storage.read_chat_meta(chatroom_id, chat_id)
    if not chat_meta:
        await safe_send({"error": "Chat not found"})
        return

    models = chat_meta.get("models_snapshot", [])
    n = min(max(data.get("n", 1), 1), 9)
    response_indices = data.get("response_indices")
    turn_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    await safe_send({
        "type": "turn_start",
        "turn_id": turn_id,
        "content": content,
    })

    final_responses: dict[tuple[str, int], dict] = {}

    async def stream_model(model_cfg: dict, response_index: int):
        model_id = model_cfg["id"]
        room = ChatRoom(_storage, _config, chatroom_id)
        try:
            async for chunk in room.stream_message(
                chat_id, content, model_cfg, response_indices
            ):
                msg = {
                    "type": "chunk",
                    "turn_id": turn_id,
                    "model_id": model_id,
                    "response_index": response_index,
                    "delta": chunk.delta,
                    "done": chunk.done,
                }
                if chunk.done and chunk.response:
                    r = chunk.response
                    resp_data = {
                        "tokens_in": r.tokens_in,
                        "tokens_out": r.tokens_out,
                        "cost": r.cost,
                        "duration_ms": r.duration_ms,
                        "tokens_per_sec": r.tokens_per_sec,
                    }
                    msg["metadata"] = resp_data
                    final_responses[(model_id, response_index)] = {
                        "model_id": model_id,
                        "response_index": response_index,
                        "content": r.content,
                        **resp_data,
                    }
                await safe_send(msg)
        except Exception as e:
            await safe_send({
                "type": "error",
                "turn_id": turn_id,
                "model_id": model_id,
                "response_index": response_index,
                "error": str(e),
            })
            final_responses[(model_id, response_index)] = {
                "model_id": model_id,
                "response_index": response_index,
                "content": str(e),
                "error": True,
            }

    tasks = []
    for m in models:
        for idx in range(n):
            tasks.append(stream_model(m, idx))

    await asyncio.gather(*tasks, return_exceptions=True)

    responses = []
    for m in models:
        for idx in range(n):
            key = (m["id"], idx)
            responses.append(
                final_responses.get(key, {
                    "model_id": m["id"],
                    "response_index": idx,
                    "content": "",
                    "error": True,
                })
            )

    turn = {
        "id": turn_id,
        "role": "user",
        "content": content,
        "created_at": now,
        "responses": responses,
        "response_indices": response_indices,
    }
    _storage.append_chat_message(chatroom_id, chat_id, turn)

    await safe_send({
        "type": "turn_complete",
        "turn_id": turn_id,
        "turn": turn,
    })


async def _handle_regenerate(
    ws: WebSocket, safe_send, chatroom_id: str, chat_id: str, data: dict
):
    turn_id = data.get("turn_id", "")
    n = min(max(data.get("n", 1), 1), 9)

    if not turn_id:
        await safe_send({"error": "turn_id required for regenerate"})
        return

    chat_meta = _storage.read_chat_meta(chatroom_id, chat_id)
    if not chat_meta:
        await safe_send({"error": "Chat not found"})
        return

    messages = _storage.read_chat_messages(chatroom_id, chat_id)
    turn = None
    turn_index = -1
    for i, msg in enumerate(messages):
        if msg["id"] == turn_id:
            turn = msg
            turn_index = i
            break

    if turn is None:
        await safe_send({"error": "Turn not found"})
        return

    models = chat_meta.get("models_snapshot", [])
    existing_responses = turn.get("responses", [])

    # Compute starting response_index per model (max existing + 1)
    max_indices: dict[str, int] = {}
    for r in existing_responses:
        mid = r["model_id"]
        ridx = r.get("response_index", 0)
        max_indices[mid] = max(max_indices.get(mid, -1), ridx)

    final_responses: dict[tuple[str, int], dict] = {}

    async def stream_model(model_cfg: dict, response_index: int):
        model_id = model_cfg["id"]
        room = ChatRoom(_storage, _config, chatroom_id)
        try:
            async for chunk in room.stream_message(
                chat_id, turn["content"], model_cfg
            ):
                msg = {
                    "type": "chunk",
                    "turn_id": turn_id,
                    "model_id": model_id,
                    "response_index": response_index,
                    "delta": chunk.delta,
                    "done": chunk.done,
                }
                if chunk.done and chunk.response:
                    r = chunk.response
                    resp_data = {
                        "tokens_in": r.tokens_in,
                        "tokens_out": r.tokens_out,
                        "cost": r.cost,
                        "duration_ms": r.duration_ms,
                        "tokens_per_sec": r.tokens_per_sec,
                    }
                    msg["metadata"] = resp_data
                    final_responses[(model_id, response_index)] = {
                        "model_id": model_id,
                        "response_index": response_index,
                        "content": r.content,
                        **resp_data,
                    }
                await safe_send(msg)
        except Exception as e:
            await safe_send({
                "type": "error",
                "turn_id": turn_id,
                "model_id": model_id,
                "response_index": response_index,
                "error": str(e),
            })
            final_responses[(model_id, response_index)] = {
                "model_id": model_id,
                "response_index": response_index,
                "content": str(e),
                "error": True,
            }

    tasks = []
    for m in models:
        start_idx = max_indices.get(m["id"], -1) + 1
        for idx in range(start_idx, start_idx + n):
            tasks.append(stream_model(m, idx))

    await asyncio.gather(*tasks, return_exceptions=True)

    # Append new responses to the existing turn
    new_responses = []
    for m in models:
        start_idx = max_indices.get(m["id"], -1) + 1
        for idx in range(start_idx, start_idx + n):
            key = (m["id"], idx)
            new_responses.append(
                final_responses.get(key, {
                    "model_id": m["id"],
                    "response_index": idx,
                    "content": "",
                    "error": True,
                })
            )

    turn["responses"] = existing_responses + new_responses
    messages[turn_index] = turn
    _storage.write_chat_messages(chatroom_id, chat_id, messages)

    await safe_send({
        "type": "turn_updated",
        "turn_id": turn_id,
        "turn": turn,
    })
