"""FastAPI routes for provider/config management."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tukey.config import ConfigManager

router = APIRouter(prefix="/api/config", tags=["config"])

# Will be set by app factory
_config: ConfigManager | None = None


def init(config: ConfigManager) -> None:
    global _config
    _config = config


def _cm() -> ConfigManager:
    assert _config is not None
    return _config


class ProviderCreate(BaseModel):
    provider: str
    api_key: str
    base_url: str | None = None
    display_name: str | None = None
    strip_model_prefix: bool = False


class ProviderUpdate(BaseModel):
    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    display_name: str | None = None
    strip_model_prefix: bool | None = None


@router.get("/providers")
def list_providers():
    return _cm().list_providers()


@router.get("/providers/{provider_id}")
def get_provider(provider_id: str):
    p = _cm().get_provider(provider_id)
    if not p:
        raise HTTPException(404, "Provider not found")
    return p


@router.post("/providers", status_code=201)
def create_provider(body: ProviderCreate):
    return _cm().add_provider(
        provider=body.provider,
        api_key=body.api_key,
        base_url=body.base_url,
        display_name=body.display_name,
        strip_model_prefix=body.strip_model_prefix,
    )


@router.patch("/providers/{provider_id}")
def update_provider(provider_id: str, body: ProviderUpdate):
    updates = body.model_dump(exclude_none=True)
    result = _cm().update_provider(provider_id, updates)
    if not result:
        raise HTTPException(404, "Provider not found")
    return result


@router.delete("/providers/{provider_id}", status_code=204)
def delete_provider(provider_id: str):
    if not _cm().remove_provider(provider_id):
        raise HTTPException(404, "Provider not found")


@router.post("/providers/{provider_id}/test")
async def test_provider(provider_id: str):
    """Minimal API call to verify provider credentials."""
    import httpx

    p = _cm().get_provider(provider_id)
    if not p:
        raise HTTPException(404, "Provider not found")
    base = (p.get("base_url") or "https://api.openai.com/v1").rstrip("/")
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{base}/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1,
                },
                headers={
                    "Authorization": f"Bearer {p['api_key']}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
            r.raise_for_status()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


class QuickSetupRequest(BaseModel):
    api_key: str
    provider: str = "openrouter"
    base_url: str | None = None
    display_name: str | None = None
    models: list[dict] = []
    chatroom_name: str = "My First Comparison"


@router.post("/quick-setup", status_code=201)
def quick_setup(body: QuickSetupRequest):
    """One-call onboarding: create provider + chatroom with models."""
    from tukey.chat.room import ChatRoom
    from tukey.storage import Storage

    cm = _cm()

    # 1. Create provider
    provider = cm.add_provider(
        provider=body.provider,
        api_key=body.api_key,
        base_url=body.base_url,
        display_name=body.display_name or body.provider.title(),
    )
    provider_id = provider["id"]

    # 2. Create chatroom with models attached to this provider
    # Import storage from the app's init — we need it for ChatRoom
    # Access via the chat route's storage (shared instance)
    from tukey.server.routes import chat as chat_routes
    storage, _ = chat_routes._get_deps()

    models = []
    for m in body.models:
        models.append({
            "id": str(uuid.uuid4()),
            "provider_id": provider_id,
            "model_id": m.get("model_id", ""),
            "display_name": m.get("display_name", m.get("model_id", "")),
            "system_prompt": m.get("system_prompt", ""),
            "temperature": m.get("temperature", 1.0),
            "max_tokens": m.get("max_tokens"),
            "top_p": m.get("top_p"),
            "extra_params": m.get("extra_params", {}),
        })

    room = ChatRoom(storage, cm)
    chatroom = room.create(name=body.chatroom_name, models=models)

    # 3. Create a first chat in the chatroom
    room_with_id = ChatRoom(storage, cm, chatroom["id"])
    chat = room_with_id.create_chat(name="Chat 1")

    return {
        "provider": provider,
        "chatroom": chatroom,
        "chat": chat,
    }
