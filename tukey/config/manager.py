"""Config manager: load/save/validate API keys and provider settings."""

from __future__ import annotations

import uuid
from typing import Any

from tukey.storage import Storage


class ConfigManager:
    def __init__(self, storage: Storage):
        self.storage = storage

    def load(self) -> dict[str, Any]:
        cfg = self.storage.read_config()
        cfg.setdefault("providers", [])
        return cfg

    def save(self, cfg: dict[str, Any]) -> None:
        self.storage.write_config(cfg)

    def list_providers(self) -> list[dict[str, Any]]:
        return self.load()["providers"]

    def get_provider(self, provider_id: str) -> dict[str, Any] | None:
        for p in self.list_providers():
            if p["id"] == provider_id:
                return p
        return None

    def add_provider(
        self,
        provider: str,
        api_key: str,
        base_url: str | None = None,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        cfg = self.load()
        entry = {
            "id": str(uuid.uuid4()),
            "provider": provider,
            "api_key": api_key,
            "base_url": base_url,
            "display_name": display_name or provider,
        }
        cfg["providers"].append(entry)
        self.save(cfg)
        return entry

    def update_provider(
        self, provider_id: str, updates: dict[str, Any]
    ) -> dict[str, Any] | None:
        cfg = self.load()
        for p in cfg["providers"]:
            if p["id"] == provider_id:
                p.update(updates)
                self.save(cfg)
                return p
        return None

    def remove_provider(self, provider_id: str) -> bool:
        cfg = self.load()
        before = len(cfg["providers"])
        cfg["providers"] = [
            p for p in cfg["providers"] if p["id"] != provider_id
        ]
        if len(cfg["providers"]) < before:
            self.save(cfg)
            return True
        return False
