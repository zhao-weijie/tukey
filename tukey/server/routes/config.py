"""FastAPI routes for provider/config management."""

from __future__ import annotations

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


class ProviderUpdate(BaseModel):
    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    display_name: str | None = None


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
