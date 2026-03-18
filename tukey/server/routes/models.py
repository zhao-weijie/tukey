"""FastAPI routes for listing available models from providers."""

from __future__ import annotations

from fastapi import APIRouter

from tukey.config import ConfigManager

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
