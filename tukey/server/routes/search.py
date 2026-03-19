"""Search across chatrooms, chats, and messages."""

from __future__ import annotations

from fastapi import APIRouter, Query

from tukey.storage import Storage

router = APIRouter(prefix="/api", tags=["search"])

_storage: Storage | None = None


def init(storage: Storage) -> None:
    global _storage
    _storage = storage


def _snippet(text: str, query: str, width: int = 80) -> str:
    lower = text.lower()
    idx = lower.find(query.lower())
    if idx == -1:
        return text[:width]
    start = max(0, idx - width // 2)
    end = min(len(text), start + width)
    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


@router.get("/search")
def search(q: str = Query(..., min_length=1), limit: int = Query(50, ge=1, le=200)):
    assert _storage is not None
    query_lower = q.lower()
    results: list[dict] = []

    for cr_id in _storage.list_chatrooms():
        if len(results) >= limit:
            break
        cr_meta = _storage.read_chatroom_meta(cr_id)
        if not cr_meta:
            continue
        cr_name = cr_meta.get("name", "")

        # Match chatroom name
        if query_lower in cr_name.lower():
            results.append({
                "type": "chatroom",
                "chatroom_id": cr_id,
                "chatroom_name": cr_name,
                "match": "chatroom_name",
                "snippet": _snippet(cr_name, q),
            })

        # Search chats and messages
        for chat_id in _storage.list_chats(cr_id):
            if len(results) >= limit:
                break
            chat_meta = _storage.read_chat_meta(cr_id, chat_id)
            if not chat_meta:
                continue
            chat_name = chat_meta.get("name", "")

            if query_lower in chat_name.lower():
                results.append({
                    "type": "chat",
                    "chatroom_id": cr_id,
                    "chatroom_name": cr_name,
                    "chat_id": chat_id,
                    "chat_name": chat_name,
                    "match": "chat_name",
                    "snippet": _snippet(chat_name, q),
                })

            messages = _storage.read_chat_messages(cr_id, chat_id)
            for msg in messages:
                if len(results) >= limit:
                    break
                content = msg.get("content", "")
                if query_lower in content.lower():
                    results.append({
                        "type": "message",
                        "chatroom_id": cr_id,
                        "chatroom_name": cr_name,
                        "chat_id": chat_id,
                        "chat_name": chat_name,
                        "message_id": msg.get("id"),
                        "match": "message_content",
                        "snippet": _snippet(content, q),
                    })
                for resp in msg.get("responses", []):
                    if len(results) >= limit:
                        break
                    rc = resp.get("content", "")
                    if query_lower in rc.lower():
                        results.append({
                            "type": "message",
                            "chatroom_id": cr_id,
                            "chatroom_name": cr_name,
                            "chat_id": chat_id,
                            "chat_name": chat_name,
                            "message_id": msg.get("id"),
                            "match": "response_content",
                            "snippet": _snippet(rc, q),
                        })

    return {"results": results[:limit]}
