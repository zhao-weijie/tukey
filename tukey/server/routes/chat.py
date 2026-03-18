"""FastAPI routes for chatroom CRUD and messaging."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tukey.chat.room import ChatRoom
from tukey.config import ConfigManager
from tukey.storage import Storage

router = APIRouter(prefix="/api/chat", tags=["chat"])

_storage: Storage | None = None
_config: ConfigManager | None = None


def init(storage: Storage, config: ConfigManager) -> None:
    global _storage, _config
    _storage = storage
    _config = config


def _get_deps() -> tuple[Storage, ConfigManager]:
    assert _storage and _config
    return _storage, _config


class RoomCreate(BaseModel):
    name: str
    models: list[dict] = []


class RoomUpdate(BaseModel):
    name: str | None = None
    models: list[dict] | None = None


class MessageSend(BaseModel):
    content: str


@router.get("/rooms")
def list_rooms():
    s, _ = _get_deps()
    rooms = []
    for rid in s.list_rooms():
        meta = s.read_room_meta(rid)
        if meta:
            rooms.append(meta)
    return rooms


@router.post("/rooms", status_code=201)
def create_room(body: RoomCreate):
    s, c = _get_deps()
    room = ChatRoom(s, c)
    return room.create(name=body.name, models=body.models)


@router.get("/rooms/{room_id}")
def get_room(room_id: str):
    s, c = _get_deps()
    meta = s.read_room_meta(room_id)
    if not meta:
        raise HTTPException(404, "Room not found")
    return meta


@router.patch("/rooms/{room_id}")
def update_room(room_id: str, body: RoomUpdate):
    s, c = _get_deps()
    meta = s.read_room_meta(room_id)
    if not meta:
        raise HTTPException(404, "Room not found")
    room = ChatRoom(s, c, room_id)
    updates = body.model_dump(exclude_none=True)
    return room.update_meta(updates)


@router.delete("/rooms/{room_id}", status_code=204)
def delete_room(room_id: str):
    s, _ = _get_deps()
    if room_id not in s.list_rooms():
        raise HTTPException(404, "Room not found")
    s.delete_room(room_id)


@router.get("/rooms/{room_id}/messages")
def get_messages(room_id: str):
    s, _ = _get_deps()
    if room_id not in s.list_rooms():
        raise HTTPException(404, "Room not found")
    return s.read_messages(room_id)


@router.post("/rooms/{room_id}/messages")
async def send_message(room_id: str, body: MessageSend):
    s, c = _get_deps()
    if room_id not in s.list_rooms():
        raise HTTPException(404, "Room not found")
    room = ChatRoom(s, c, room_id)
    return await room.send_message(body.content)
