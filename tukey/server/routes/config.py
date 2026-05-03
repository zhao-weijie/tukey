"""FastAPI routes for provider/config management."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tukey.config import ConfigManager
from tukey.core import contracts
from tukey.storage import Storage

router = APIRouter(prefix="/api/config", tags=["config"])

_config: ConfigManager | None = None
_storage: Storage | None = None


def init(config: ConfigManager, storage: Storage | None = None) -> None:
    global _config, _storage
    _config = config
    if storage is not None:
        _storage = storage


def _cm() -> ConfigManager:
    assert _config is not None
    return _config


def _s() -> Storage:
    assert _storage is not None
    return _storage


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


def _mask_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    if len(api_key) <= 10:
        return "*" * len(api_key)
    return f"{api_key[:6]}...{api_key[-4:]}"


def _public_provider(provider: dict) -> dict:
    return {
        **provider,
        "api_key": _mask_api_key(provider.get("api_key")),
        "api_key_present": bool(provider.get("api_key")),
    }


@router.get("/providers")
def list_providers():
    return [_public_provider(provider) for provider in _cm().list_providers()]


@router.get("/providers/{provider_id}")
def get_provider(provider_id: str):
    p = _cm().get_provider(provider_id)
    if not p:
        raise HTTPException(404, "Provider not found")
    return _public_provider(p)


@router.post("/providers", status_code=201)
def create_provider(body: ProviderCreate):
    provider = _cm().add_provider(
        provider=body.provider,
        api_key=body.api_key,
        base_url=body.base_url,
        display_name=body.display_name,
        strip_model_prefix=body.strip_model_prefix,
    )
    return _public_provider(provider)


@router.patch("/providers/{provider_id}")
def update_provider(provider_id: str, body: ProviderUpdate):
    updates = body.model_dump(exclude_none=True)
    result = _cm().update_provider(provider_id, updates)
    if not result:
        raise HTTPException(404, "Provider not found")
    return _public_provider(result)


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
    task_name: str | None = None
    config_set_name: str | None = None
    chain_name: str | None = None


@router.post("/quick-setup", status_code=201)
def quick_setup(body: QuickSetupRequest):
    """One-call onboarding: create provider, config set, task, and chain."""
    cm = _cm()
    storage = _s()

    provider = cm.add_provider(
        provider=body.provider,
        api_key=body.api_key,
        base_url=body.base_url,
        display_name=body.display_name or body.provider.title(),
    )
    provider_id = provider["id"]

    config_set = contracts.make_config_set({
        "name": body.config_set_name or body.chatroom_name,
        "description": "Created by quick setup",
        "tags": ["quickstart"],
    })
    storage.write_config_set_meta(config_set["id"], config_set)

    slots = [
        contracts.make_config_slot(config_set["id"], {
            "provider_id": provider_id,
            "model_id": m.get("model_id", ""),
            "display_name": m.get("display_name", m.get("model_id", "")),
            "system_prompt": m.get("system_prompt", ""),
            "temperature": m.get("temperature", 1.0),
            "max_tokens": m.get("max_tokens"),
            "top_p": m.get("top_p"),
            "extra_params": m.get("extra_params", {}),
            "task_type": m.get("task_type", "chat_completion"),
            "modality": m.get("modality", "text"),
        })
        for m in body.models
    ]
    storage.write_config_slots(config_set["id"], slots)
    config_set["slot_order"] = [slot["id"] for slot in slots]
    config_set["updated_at"] = contracts.utc_now()
    storage.write_config_set_meta(config_set["id"], config_set)

    task = contracts.make_task({
        "name": body.task_name or body.chatroom_name,
        "description": "Quick-start comparison task",
        "tags": ["quickstart"],
        "default_config_set_id": config_set["id"],
    })
    storage.write_task_meta(task["id"], task)

    chain = contracts.make_run_chain({
        "name": body.chain_name or body.chatroom_name,
        "default_config_set_id": config_set["id"],
    })
    storage.write_run_chain_meta(chain["id"], chain)
    storage.write_run_chain_view_state(chain["id"], {
        "chain_id": chain["id"],
        "selected_outputs": {},
        "pinned_output_ids": [],
        "collapsed_run_ids": [],
    })

    return {
        "provider": _public_provider(provider),
        "config_set": config_set,
        "slots": slots,
        "task": task,
        "chain": chain,
    }
