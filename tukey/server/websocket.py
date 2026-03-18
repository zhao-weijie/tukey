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


@router.websocket("/ws/chat/{room_id}")
async def chat_stream(ws: WebSocket, room_id: str):
    assert _storage and _config
    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            content = data.get("content", "")
            if not content:
                continue

            meta = _storage.read_room_meta(room_id)
            if not meta:
                await ws.send_json({"error": "Room not found"})
                continue

            models = meta.get("models", [])
            turn_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()

            await ws.send_json({
                "type": "turn_start",
                "turn_id": turn_id,
                "content": content,
            })

            # Collect final responses from each model for persistence
            final_responses: dict[str, dict] = {}

            async def stream_model(model_cfg: dict):
                model_id = model_cfg["id"]
                room = ChatRoom(_storage, _config, room_id)
                try:
                    async for chunk in room.stream_message(content, model_cfg):
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

            # Persist once from streamed results (no duplicate call)
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
            _storage.append_message(room_id, turn)

            await ws.send_json({
                "type": "turn_complete",
                "turn_id": turn_id,
                "turn": turn,
            })

    except WebSocketDisconnect:
        pass
