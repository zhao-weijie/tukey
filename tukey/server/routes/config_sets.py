"""FastAPI routes for run-native config sets and immutable versions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tukey.config import ConfigManager
from tukey.core import contracts
from tukey.storage import Storage

router = APIRouter(prefix="/api/config-sets", tags=["config-sets"])

_storage: Storage | None = None
_config: ConfigManager | None = None


def init(storage: Storage, config: ConfigManager) -> None:
    global _storage, _config
    _storage = storage
    _config = config


def _deps() -> tuple[Storage, ConfigManager]:
    assert _storage is not None and _config is not None
    return _storage, _config


class ConfigSetCreate(BaseModel):
    name: str
    description: str | None = None
    tags: list[str] = []


class ConfigSetUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    slot_order: list[str] | None = None
    archived: bool | None = None


class ConfigSlotCreate(BaseModel):
    name: str | None = None
    provider_id: str
    provider_model_id: str
    display_name: str | None = None
    system_prompt: str = ""
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    extra_params: dict = {}
    response_format: dict | None = None
    tools: list[dict] | None = None
    tool_choice: object | None = None
    mcp_server_ids: list[str] | None = None
    modality: str = "text"
    task_type: str = "chat_completion"
    enabled: bool = True


class ConfigSlotUpdate(BaseModel):
    name: str | None = None
    provider_id: str | None = None
    provider_model_id: str | None = None
    display_name: str | None = None
    system_prompt: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    extra_params: dict | None = None
    response_format: dict | None = None
    tools: list[dict] | None = None
    tool_choice: object | None = None
    mcp_server_ids: list[str] | None = None
    modality: str | None = None
    task_type: str | None = None
    enabled: bool | None = None


class FreezeConfigVersion(BaseModel):
    slot_id: str
    first_used_run_id: str | None = None
    created_by: str = "system"


def _require_config_set(storage: Storage, config_set_id: str) -> dict:
    config_set = storage.read_config_set_meta(config_set_id)
    if not config_set:
        raise HTTPException(404, "Config set not found")
    return config_set


def _find_slot(storage: Storage, config_set_id: str, slot_id: str) -> tuple[list[dict], dict]:
    slots = storage.read_config_slots(config_set_id)
    for slot in slots:
        if slot["id"] == slot_id:
            return slots, slot
    raise HTTPException(404, "Config slot not found")


def _validate_provider(config: ConfigManager, provider_id: str) -> dict:
    provider = config.get_provider(provider_id)
    if not provider:
        raise HTTPException(422, "Provider not found")
    return provider


def _validate_mcp_servers(config: ConfigManager, server_ids: list[str] | None) -> list[dict]:
    servers = []
    for server_id in server_ids or []:
        server = config.get_mcp_server(server_id)
        if not server:
            raise HTTPException(422, f"MCP server not found: {server_id}")
        servers.append(server)
    return servers


def _validate_slot_references(config: ConfigManager, slot: dict) -> tuple[dict, list[dict]]:
    provider = _validate_provider(config, slot["provider_id"])
    mcp_servers = _validate_mcp_servers(config, slot.get("mcp_server_ids"))
    return provider, mcp_servers


@router.get("")
def list_config_sets():
    storage, _ = _deps()
    config_sets = []
    for config_set_id in storage.list_config_sets():
        meta = storage.read_config_set_meta(config_set_id)
        if meta:
            config_sets.append(meta)
    return config_sets


@router.post("", status_code=201)
def create_config_set(body: ConfigSetCreate):
    storage, _ = _deps()
    config_set = contracts.make_config_set(body.model_dump())
    storage.write_config_set_meta(config_set["id"], config_set)
    storage.write_config_slots(config_set["id"], [])
    return config_set


@router.get("/{config_set_id}")
def get_config_set(config_set_id: str):
    storage, _ = _deps()
    return _require_config_set(storage, config_set_id)


@router.patch("/{config_set_id}")
def update_config_set(config_set_id: str, body: ConfigSetUpdate):
    storage, _ = _deps()
    config_set = _require_config_set(storage, config_set_id)
    updates = body.model_dump(exclude_unset=True)
    if "slot_order" in updates:
        slot_ids = {slot["id"] for slot in storage.read_config_slots(config_set_id)}
        unknown = [slot_id for slot_id in updates["slot_order"] if slot_id not in slot_ids]
        if unknown:
            raise HTTPException(422, f"Unknown slot IDs in slot_order: {unknown}")
    config_set.update(updates)
    config_set["updated_at"] = contracts.utc_now()
    storage.write_config_set_meta(config_set_id, config_set)
    return config_set


@router.delete("/{config_set_id}", status_code=204)
def delete_config_set(config_set_id: str):
    storage, _ = _deps()
    config_set = _require_config_set(storage, config_set_id)
    config_set["archived"] = True
    config_set["updated_at"] = contracts.utc_now()
    storage.write_config_set_meta(config_set_id, config_set)


@router.get("/{config_set_id}/slots")
def list_config_slots(config_set_id: str):
    storage, _ = _deps()
    _require_config_set(storage, config_set_id)
    return storage.read_config_slots(config_set_id)


@router.post("/{config_set_id}/slots", status_code=201)
def create_config_slot(config_set_id: str, body: ConfigSlotCreate):
    storage, config = _deps()
    config_set = _require_config_set(storage, config_set_id)
    slot = contracts.make_config_slot(config_set_id, body.model_dump())
    _validate_slot_references(config, slot)
    slots = storage.read_config_slots(config_set_id)
    slots.append(slot)
    storage.write_config_slots(config_set_id, slots)
    config_set["slot_order"] = [*config_set.get("slot_order", []), slot["id"]]
    config_set["updated_at"] = contracts.utc_now()
    storage.write_config_set_meta(config_set_id, config_set)
    return slot


@router.patch("/{config_set_id}/slots/{slot_id}")
def update_config_slot(config_set_id: str, slot_id: str, body: ConfigSlotUpdate):
    storage, config = _deps()
    config_set = _require_config_set(storage, config_set_id)
    slots, slot = _find_slot(storage, config_set_id, slot_id)
    updates = body.model_dump(exclude_unset=True)
    slot.update(updates)
    if "provider_model_id" in updates and "display_name" not in updates:
        slot["display_name"] = updates["provider_model_id"]
    _validate_slot_references(config, slot)
    slot["updated_at"] = contracts.utc_now()
    storage.write_config_slots(config_set_id, slots)

    order = config_set.get("slot_order", [])
    if slot.get("enabled", True) and slot_id not in order:
        config_set["slot_order"] = [*order, slot_id]
    elif not slot.get("enabled", True):
        config_set["slot_order"] = [existing for existing in order if existing != slot_id]
    config_set["updated_at"] = contracts.utc_now()
    storage.write_config_set_meta(config_set_id, config_set)
    return slot


@router.delete("/{config_set_id}/slots/{slot_id}", status_code=204)
def delete_config_slot(config_set_id: str, slot_id: str):
    storage, _ = _deps()
    config_set = _require_config_set(storage, config_set_id)
    slots, slot = _find_slot(storage, config_set_id, slot_id)
    slot["enabled"] = False
    slot["updated_at"] = contracts.utc_now()
    storage.write_config_slots(config_set_id, slots)
    config_set["slot_order"] = [
        existing for existing in config_set.get("slot_order", [])
        if existing != slot_id
    ]
    config_set["updated_at"] = contracts.utc_now()
    storage.write_config_set_meta(config_set_id, config_set)


@router.get("/{config_set_id}/versions")
def list_config_versions(config_set_id: str):
    storage, _ = _deps()
    _require_config_set(storage, config_set_id)
    return storage.read_config_versions(config_set_id)


@router.post("/{config_set_id}/versions:freeze", status_code=201)
def freeze_config_version(config_set_id: str, body: FreezeConfigVersion):
    storage, config = _deps()
    _require_config_set(storage, config_set_id)
    _, slot = _find_slot(storage, config_set_id, body.slot_id)
    provider, mcp_servers = _validate_slot_references(config, slot)
    return storage.freeze_config_version(
        config_set_id,
        slot,
        provider,
        mcp_servers,
        first_used_run_id=body.first_used_run_id,
        created_by=body.created_by,
    )
