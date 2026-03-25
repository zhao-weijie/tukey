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
        cfg.setdefault("mcp_servers", [])
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
        strip_model_prefix: bool = False,
    ) -> dict[str, Any]:
        cfg = self.load()
        entry = {
            "id": str(uuid.uuid4()),
            "provider": provider,
            "api_key": api_key,
            "base_url": base_url,
            "display_name": display_name or provider,
            "strip_model_prefix": strip_model_prefix,
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

    # --- MCP Servers ---

    def list_mcp_servers(self) -> list[dict[str, Any]]:
        return self.load()["mcp_servers"]

    def get_mcp_server(self, server_id: str) -> dict[str, Any] | None:
        for s in self.list_mcp_servers():
            if s["id"] == server_id:
                return s
        return None

    def add_mcp_server(
        self,
        name: str,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        cfg = self.load()
        entry = {
            "id": str(uuid.uuid4()),
            "name": name,
            "command": command,
            "args": args or [],
            "env": env or {},
            "enabled": True,
        }
        cfg["mcp_servers"].append(entry)
        self.save(cfg)
        return entry

    def update_mcp_server(
        self, server_id: str, updates: dict[str, Any]
    ) -> dict[str, Any] | None:
        cfg = self.load()
        for s in cfg["mcp_servers"]:
            if s["id"] == server_id:
                s.update(updates)
                self.save(cfg)
                return s
        return None

    def remove_mcp_server(self, server_id: str) -> bool:
        cfg = self.load()
        before = len(cfg["mcp_servers"])
        cfg["mcp_servers"] = [
            s for s in cfg["mcp_servers"] if s["id"] != server_id
        ]
        if len(cfg["mcp_servers"]) < before:
            self.save(cfg)
            return True
        return False
