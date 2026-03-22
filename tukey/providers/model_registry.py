"""Model registry: pricing + capabilities from LiteLLM's public JSON."""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

PRICING_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm"
    "/main/model_prices_and_context_window.json"
)
CACHE_PATH = Path.home() / ".tukey" / "model_prices.json"
CACHE_TTL = 86400  # 24 hours

_registry: dict | None = None
_loaded_at: float = 0


def _load() -> dict:
    global _registry, _loaded_at
    if _registry is not None and (time.time() - _loaded_at) < CACHE_TTL:
        return _registry

    # Try cache file first
    if CACHE_PATH.exists():
        age = time.time() - CACHE_PATH.stat().st_mtime
        if age < CACHE_TTL:
            _registry = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            _loaded_at = time.time()
            return _registry

    # Fetch fresh
    try:
        resp = httpx.get(PRICING_URL, timeout=10)
        resp.raise_for_status()
        _registry = resp.json()
        # Remove the "sample_spec" key that litellm includes
        _registry.pop("sample_spec", None)
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(_registry), encoding="utf-8")
        _loaded_at = time.time()
        return _registry
    except Exception:
        # Fall back to stale cache
        if CACHE_PATH.exists():
            _registry = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            _registry.pop("sample_spec", None)
            _loaded_at = time.time()
            return _registry
        # No cache, no network — return empty
        _registry = {}
        _loaded_at = time.time()
        return _registry


def _lookup(model_id: str) -> dict | None:
    """Look up model by exact key, then try stripping provider prefix."""
    reg = _load()
    if model_id in reg:
        return reg[model_id]
    # Strip "openai/" or other provider prefixes
    if "/" in model_id:
        bare = model_id.split("/", 1)[1]
        if bare in reg:
            return reg[bare]
    return None


def get_model_info(model_id: str) -> dict | None:
    return _lookup(model_id)


def compute_cost(model_id: str, tokens_in: int, tokens_out: int) -> float | None:
    info = _lookup(model_id)
    if not info:
        return None
    input_cost = info.get("input_cost_per_token")
    output_cost = info.get("output_cost_per_token")
    if input_cost is None or output_cost is None:
        return None
    return tokens_in * input_cost + tokens_out * output_cost


def get_capabilities(model_id: str) -> dict:
    info = _lookup(model_id)
    if not info:
        return {
            "supports_reasoning": False,
            "supports_vision": False,
            "max_tokens": None,
            "max_input_tokens": None,
        }
    return {
        "supports_reasoning": info.get("supports_reasoning", False),
        "supports_vision": info.get("supports_vision", False),
        "max_tokens": info.get("max_tokens"),
        "max_input_tokens": info.get("max_input_tokens"),
    }
