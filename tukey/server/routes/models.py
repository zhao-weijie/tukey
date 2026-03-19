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


@router.get("/{model_id:path}/capabilities")
def get_model_capabilities(model_id: str):
    """Return capability flags for a model via litellm."""
    try:
        import litellm

        info = litellm.get_model_info(model_id)
        return {
            "supports_reasoning": info.get("supports_reasoning", False),
            "supports_vision": info.get("supports_vision", False),
            "max_tokens": info.get("max_tokens"),
            "max_input_tokens": info.get("max_input_tokens"),
        }
    except Exception:
        return {
            "supports_reasoning": False,
            "supports_vision": False,
            "max_tokens": None,
            "max_input_tokens": None,
        }
