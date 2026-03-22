"""FastAPI routes for listing available models from providers."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

import httpx

from tukey.config import ConfigManager
from tukey.providers import model_registry

router = APIRouter(prefix="/api/models", tags=["models"])

_config: ConfigManager | None = None


def init(config: ConfigManager) -> None:
    global _config
    _config = config


@router.get("")
def list_models():
    """Return configured providers (for model selection in UI)."""
    assert _config is not None
    return _config.list_providers()


@router.get("/providers/{provider_id}/available")
def get_available_models(provider_id: str):
    """List models available from a provider."""
    assert _config is not None
    prov = _config.get_provider(provider_id)
    if not prov:
        raise HTTPException(404, "Provider not found")

    if prov.get("base_url"):
        # Gateway: query /models endpoint
        try:
            r = httpx.get(
                f"{prov['base_url'].rstrip('/')}/models",
                headers={"Authorization": f"Bearer {prov['api_key']}"},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json().get("data", [])
            return [{"id": m["id"], "name": m.get("id", "")} for m in data]
        except Exception:
            return []
    else:
        # Native provider without gateway — no model listing available
        return []


@router.get("/{model_id:path}/capabilities")
def get_model_capabilities(model_id: str):
    """Return capability flags for a model via the model registry."""
    return model_registry.get_capabilities(model_id)
