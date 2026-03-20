"""FastAPI routes for chatroom and chat CRUD."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
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


class ChatroomCreate(BaseModel):
    name: str
    models: list[dict] = []


class ChatroomUpdate(BaseModel):
    name: str | None = None
    models: list[dict] | None = None


class ChatCreate(BaseModel):
    name: str | None = None


class ChatUpdate(BaseModel):
    name: str | None = None


class MessageSend(BaseModel):
    content: str


# --- Chatroom endpoints ---

@router.get("/chatrooms")
def list_chatrooms():
    s, _ = _get_deps()
    chatrooms = []
    for cid in s.list_chatrooms():
        meta = s.read_chatroom_meta(cid)
        if meta:
            chatrooms.append(meta)
    return chatrooms


@router.post("/chatrooms", status_code=201)
def create_chatroom(body: ChatroomCreate):
    s, c = _get_deps()
    room = ChatRoom(s, c)
    return room.create(name=body.name, models=body.models)


@router.get("/chatrooms/{chatroom_id}")
def get_chatroom(chatroom_id: str):
    s, _ = _get_deps()
    meta = s.read_chatroom_meta(chatroom_id)
    if not meta:
        raise HTTPException(404, "Chatroom not found")
    return meta


@router.patch("/chatrooms/{chatroom_id}")
def update_chatroom(chatroom_id: str, body: ChatroomUpdate):
    s, c = _get_deps()
    meta = s.read_chatroom_meta(chatroom_id)
    if not meta:
        raise HTTPException(404, "Chatroom not found")
    room = ChatRoom(s, c, chatroom_id)
    updates = body.model_dump(exclude_none=True)
    return room.update_meta(updates)


@router.delete("/chatrooms/{chatroom_id}", status_code=204)
def delete_chatroom(chatroom_id: str):
    s, _ = _get_deps()
    if chatroom_id not in s.list_chatrooms():
        raise HTTPException(404, "Chatroom not found")
    s.delete_chatroom(chatroom_id)


# --- Chat endpoints (nested under chatroom) ---

@router.get("/chatrooms/{chatroom_id}/chats")
def list_chats(chatroom_id: str):
    s, c = _get_deps()
    if chatroom_id not in s.list_chatrooms():
        raise HTTPException(404, "Chatroom not found")
    room = ChatRoom(s, c, chatroom_id)
    return room.list_chats()


@router.post("/chatrooms/{chatroom_id}/chats", status_code=201)
def create_chat(chatroom_id: str, body: ChatCreate):
    s, c = _get_deps()
    if chatroom_id not in s.list_chatrooms():
        raise HTTPException(404, "Chatroom not found")
    room = ChatRoom(s, c, chatroom_id)
    return room.create_chat(name=body.name)


@router.get("/chatrooms/{chatroom_id}/chats/{chat_id}")
def get_chat(chatroom_id: str, chat_id: str):
    s, _ = _get_deps()
    meta = s.read_chat_meta(chatroom_id, chat_id)
    if not meta:
        raise HTTPException(404, "Chat not found")
    return meta


@router.patch("/chatrooms/{chatroom_id}/chats/{chat_id}")
def update_chat(chatroom_id: str, chat_id: str, body: ChatUpdate):
    s, _ = _get_deps()
    meta = s.read_chat_meta(chatroom_id, chat_id)
    if not meta:
        raise HTTPException(404, "Chat not found")
    updates = body.model_dump(exclude_none=True)
    meta.update(updates)
    s.write_chat_meta(chatroom_id, chat_id, meta)
    return meta


@router.delete("/chatrooms/{chatroom_id}/chats/{chat_id}", status_code=204)
def delete_chat(chatroom_id: str, chat_id: str):
    s, _ = _get_deps()
    if chat_id not in s.list_chats(chatroom_id):
        raise HTTPException(404, "Chat not found")
    s.delete_chat(chatroom_id, chat_id)


@router.get("/chatrooms/{chatroom_id}/chats/{chat_id}/messages")
def get_messages(chatroom_id: str, chat_id: str):
    s, _ = _get_deps()
    if chat_id not in s.list_chats(chatroom_id):
        raise HTTPException(404, "Chat not found")
    return s.read_chat_messages(chatroom_id, chat_id)


@router.post("/chatrooms/{chatroom_id}/chats/{chat_id}/messages")
async def send_message(chatroom_id: str, chat_id: str, body: MessageSend):
    s, c = _get_deps()
    if chat_id not in s.list_chats(chatroom_id):
        raise HTTPException(404, "Chat not found")
    room = ChatRoom(s, c, chatroom_id)
    return await room.send_message(chat_id, body.content)


# --- Reproducibility ---

@router.get("/chatrooms/{chatroom_id}/chats/{chat_id}/manifest")
def get_manifest(chatroom_id: str, chat_id: str):
    s, c = _get_deps()
    if chatroom_id not in s.list_chatrooms():
        raise HTTPException(404, "Chatroom not found")
    if chat_id not in s.list_chats(chatroom_id):
        raise HTTPException(404, "Chat not found")
    room = ChatRoom(s, c, chatroom_id)
    return room.get_manifest(chat_id)


@router.post("/chatrooms/{chatroom_id}/chats/{chat_id}/replay", status_code=201)
async def replay_chat(chatroom_id: str, chat_id: str):
    s, c = _get_deps()
    if chatroom_id not in s.list_chatrooms():
        raise HTTPException(404, "Chatroom not found")
    if chat_id not in s.list_chats(chatroom_id):
        raise HTTPException(404, "Chat not found")
    room = ChatRoom(s, c, chatroom_id)
    return await room.replay_chat(chat_id)


# --- Export / Import ---

@router.get("/chatrooms/{chatroom_id}/export")
def export_chatroom(chatroom_id: str):
    s, _ = _get_deps()
    if chatroom_id not in s.list_chatrooms():
        raise HTTPException(404, "Chatroom not found")
    data = ChatRoom.export_chatroom(s, chatroom_id)
    cr_name = data["chatroom"]["name"].replace(" ", "_").lower()
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": f'attachment; filename="tukey-{cr_name}.json"'},
    )


class ChatroomImport(BaseModel):
    data: dict


@router.post("/chatrooms/import", status_code=201)
def import_chatroom(body: ChatroomImport):
    s, c = _get_deps()
    return ChatRoom.import_chatroom(s, c, body.data)
