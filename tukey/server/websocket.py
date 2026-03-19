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
    try:
        while True:
            data = await ws.receive_json()
            content = data.get("content", "")
            if not content:
                continue

            chat_meta = _storage.read_chat_meta(chatroom_id, chat_id)
            if not chat_meta:
                await ws.send_json({"error": "Chat not found"})
                continue

            models = chat_meta.get("models_snapshot", [])
            turn_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()

            await ws.send_json({
                "type": "turn_start",
                "turn_id": turn_id,
                "content": content,
            })

            final_responses: dict[str, dict] = {}

            async def stream_model(model_cfg: dict):
                model_id = model_cfg["id"]
                room = ChatRoom(_storage, _config, chatroom_id)
                try:
                    async for chunk in room.stream_message(chat_id, content, model_cfg):
                        msg = {
                            "type": "chunk",
                            "turn_id": turn_id,
                            "model_id": model_id,
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
                            final_responses[model_id] = {
                                "model_id": model_id,
                                "content": r.content,
                                **resp_data,
                            }
                        await ws.send_json(msg)
                except Exception as e:
                    await ws.send_json({
                        "type": "error",
                        "turn_id": turn_id,
                        "model_id": model_id,
                        "error": str(e),
                    })
                    final_responses[model_id] = {
                        "model_id": model_id,
                        "content": str(e),
                        "error": True,
                    }

            await asyncio.gather(
                *[stream_model(m) for m in models],
                return_exceptions=True,
            )

            responses = [
                final_responses.get(m["id"], {
                    "model_id": m["id"],
                    "content": "",
                    "error": True,
                })
                for m in models
            ]
            turn = {
                "id": turn_id,
                "role": "user",
                "content": content,
                "created_at": now,
                "responses": responses,
            }
            _storage.append_chat_message(chatroom_id, chat_id, turn)

            await ws.send_json({
                "type": "turn_complete",
                "turn_id": turn_id,
                "turn": turn,
            })

    except WebSocketDisconnect:
        pass
