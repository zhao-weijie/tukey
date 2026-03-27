"""WebSocket endpoint for streaming LLM responses."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from tukey.chat.room import ChatRoom
from tukey.config import ConfigManager
from tukey.mcp.manager import McpManager
from tukey.storage import Storage

router = APIRouter()

_storage: Storage | None = None
_config: ConfigManager | None = None
_mcp_manager: McpManager | None = None


def init(storage: Storage, config: ConfigManager, mcp_manager: McpManager) -> None:
    global _storage, _config, _mcp_manager
    _storage = storage
    _config = config
    _mcp_manager = mcp_manager


@router.websocket("/ws/chat/{chatroom_id}/{chat_id}")
async def chat_stream(ws: WebSocket, chatroom_id: str, chat_id: str):
    assert _storage and _config
    await ws.accept()
    ws_lock = asyncio.Lock()

    async def safe_send(msg: dict):
        async with ws_lock:
            try:
                await ws.send_json(msg)
            except RuntimeError:
                # WebSocket was closed (e.g., client disconnected)
                pass

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

    # For the first message, re-snapshot from the chatroom's current models
    # so config changes made after chat creation are picked up.
    existing_msgs = _storage.read_chat_messages(chatroom_id, chat_id)
    if not existing_msgs:
        chatroom_meta = _storage.read_chatroom_meta(chatroom_id)
        if chatroom_meta and chatroom_meta.get("models"):
            chat_meta["models_snapshot"] = chatroom_meta["models"]
            _storage.write_chat_meta(chatroom_id, chat_id, chat_meta)

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
        tool_interactions: list[dict] = []
        current_tool_calls: list[dict] = []
        last_content = ""
        last_metadata: dict = {}
        try:
            async for chunk in room.stream_message(
                chat_id, content, model_cfg, response_indices,
                mcp_manager=_mcp_manager,
            ):
                # Tool call info from the model
                if chunk.tool_calls:
                    current_tool_calls = [
                        {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                        for tc in chunk.tool_calls
                    ]
                    for tc in chunk.tool_calls:
                        await safe_send({
                            "type": "tool_call",
                            "turn_id": turn_id,
                            "model_id": model_id,
                            "response_index": response_index,
                            "tool_call": {
                                "id": tc.id, "name": tc.name, "arguments": tc.arguments,
                            },
                        })

                # Tool result after execution
                if chunk.tool_result:
                    tr = chunk.tool_result
                    await safe_send({
                        "type": "tool_result",
                        "turn_id": turn_id,
                        "model_id": model_id,
                        "response_index": response_index,
                        "tool_result": {
                            "tool_call_id": tr.tool_call_id,
                            "name": tr.name,
                            "result": tr.result[:2000],  # truncate for WS
                            "error": tr.error,
                        },
                    })
                    # Check if all tool results for this iteration are in
                    tool_results = [
                        e for e in tool_interactions
                        if e.get("_pending")
                    ]
                    if not tool_results:
                        tool_interactions.append({
                            "tool_calls": current_tool_calls,
                            "tool_results": [{
                                "tool_call_id": tr.tool_call_id,
                                "name": tr.name,
                                "result": tr.result[:2000],
                                "error": tr.error,
                            }],
                        })
                    else:
                        tool_interactions[-1]["tool_results"].append({
                            "tool_call_id": tr.tool_call_id,
                            "name": tr.name,
                            "result": tr.result[:2000],
                            "error": tr.error,
                        })
                    continue

                # Regular content chunk
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
                    last_content = r.content
                    last_metadata = {
                        "tokens_in": r.tokens_in,
                        "tokens_out": r.tokens_out,
                        "cost": r.cost,
                        "duration_ms": r.duration_ms,
                        "tokens_per_sec": r.tokens_per_sec,
                    }
                    # Only send metadata on the final done (no more tool calls)
                    if not chunk.tool_calls:
                        msg["metadata"] = last_metadata
                await safe_send(msg)

            # Build final response
            resp_data = {
                "model_id": model_id,
                "response_index": response_index,
                "content": last_content,
                **last_metadata,
            }
            if tool_interactions:
                resp_data["tool_interactions"] = tool_interactions
            final_responses[(model_id, response_index)] = resp_data

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
        last_content = ""
        last_metadata: dict = {}
        try:
            async for chunk in room.stream_message(
                chat_id, turn["content"], model_cfg,
                mcp_manager=_mcp_manager,
            ):
                # Tool call/result events
                if chunk.tool_calls:
                    for tc in chunk.tool_calls:
                        await safe_send({
                            "type": "tool_call",
                            "turn_id": turn_id,
                            "model_id": model_id,
                            "response_index": response_index,
                            "tool_call": {"id": tc.id, "name": tc.name, "arguments": tc.arguments},
                        })
                if chunk.tool_result:
                    tr = chunk.tool_result
                    await safe_send({
                        "type": "tool_result",
                        "turn_id": turn_id,
                        "model_id": model_id,
                        "response_index": response_index,
                        "tool_result": {
                            "tool_call_id": tr.tool_call_id, "name": tr.name,
                            "result": tr.result[:2000], "error": tr.error,
                        },
                    })
                    continue

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
                    last_content = r.content
                    last_metadata = {
                        "tokens_in": r.tokens_in,
                        "tokens_out": r.tokens_out,
                        "cost": r.cost,
                        "duration_ms": r.duration_ms,
                        "tokens_per_sec": r.tokens_per_sec,
                    }
                    if not chunk.tool_calls:
                        msg["metadata"] = last_metadata
                await safe_send(msg)

            final_responses[(model_id, response_index)] = {
                "model_id": model_id,
                "response_index": response_index,
                "content": last_content,
                **last_metadata,
            }
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
