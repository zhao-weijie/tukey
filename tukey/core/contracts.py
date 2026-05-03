"""Helpers for Tukey's run-native data contracts.

The project still has legacy chatroom and experiment surfaces. This module is
the additive contract layer for tasks, config sets, immutable config versions,
runs, run chains, and related records.
"""

from __future__ import annotations

import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from importlib.metadata import version as pkg_version
from typing import Any

import tukey


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def runtime_snapshot() -> dict[str, Any]:
    return {
        "tukey_version": tukey.__version__,
        "httpx_version": pkg_version("httpx"),
        "python_version": sys.version,
    }


def provider_snapshot(provider: dict[str, Any] | None) -> dict[str, Any]:
    if not provider:
        return {}
    return {
        "id": provider.get("id"),
        "provider": provider.get("provider"),
        "base_url": provider.get("base_url"),
        "display_name": provider.get("display_name"),
        "strip_model_prefix": provider.get("strip_model_prefix", False),
    }


def mcp_server_snapshot(server: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": server.get("id"),
        "name": server.get("name"),
        "command": server.get("command"),
        "args": server.get("args", []),
        "enabled": server.get("enabled", True),
    }


def _canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def config_slot_content_hash(
    slot_snapshot: dict[str, Any],
    provider: dict[str, Any] | None,
    mcp_servers: list[dict[str, Any]] | None = None,
) -> str:
    content = {
        "slot_snapshot": _strip_slot_volatiles(slot_snapshot),
        "provider_snapshot": provider_snapshot(provider),
        "mcp_server_snapshots": [
            mcp_server_snapshot(s) for s in (mcp_servers or [])
        ],
    }
    return hashlib.sha256(_canonical_json(content).encode("utf-8")).hexdigest()


def _strip_slot_volatiles(slot: dict[str, Any]) -> dict[str, Any]:
    return {
        k: v for k, v in slot.items()
        if k not in {"created_at", "updated_at"}
    }


def make_task(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return {
        "id": data.get("id", new_id()),
        "name": data["name"],
        "description": data.get("description"),
        "tags": data.get("tags", []),
        "default_config_set_id": data.get("default_config_set_id"),
        "created_at": data.get("created_at", now),
        "updated_at": data.get("updated_at", now),
        "archived": data.get("archived", False),
    }


def make_config_set(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return {
        "id": data.get("id", new_id()),
        "name": data["name"],
        "description": data.get("description"),
        "tags": data.get("tags", []),
        "slot_order": data.get("slot_order", []),
        "archived": data.get("archived", False),
        "created_at": data.get("created_at", now),
        "updated_at": data.get("updated_at", now),
    }


def make_config_slot(config_set_id: str, data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    provider_model_id = data.get("provider_model_id", data.get("model_id"))
    return {
        "id": data.get("id", new_id()),
        "config_set_id": config_set_id,
        "name": data.get("name", data.get("display_name", provider_model_id)),
        "provider_id": data["provider_id"],
        "provider_model_id": provider_model_id,
        "display_name": data.get("display_name", provider_model_id),
        "system_prompt": data.get("system_prompt", ""),
        "temperature": data.get("temperature"),
        "max_tokens": data.get("max_tokens"),
        "top_p": data.get("top_p"),
        "extra_params": data.get("extra_params", {}),
        "response_format": data.get("response_format"),
        "tools": data.get("tools"),
        "tool_choice": data.get("tool_choice"),
        "mcp_server_ids": data.get("mcp_server_ids"),
        "modality": data.get("modality", "text"),
        "task_type": data.get("task_type", "chat_completion"),
        "enabled": data.get("enabled", True),
        "created_at": data.get("created_at", now),
        "updated_at": data.get("updated_at", now),
    }


def make_config_version(
    *,
    config_set_id: str,
    slot_snapshot: dict[str, Any],
    provider: dict[str, Any] | None,
    mcp_servers: list[dict[str, Any]] | None,
    version: int,
    first_used_run_id: str | None = None,
    created_by: str = "system",
) -> dict[str, Any]:
    now = utc_now()
    content_hash = config_slot_content_hash(slot_snapshot, provider, mcp_servers)
    return {
        "id": new_id(),
        "config_set_id": config_set_id,
        "slot_id": slot_snapshot["id"],
        "version": version,
        "content_hash": content_hash,
        "created_at": now,
        "created_by": created_by,
        "first_used_run_id": first_used_run_id,
        "slot_snapshot": dict(slot_snapshot),
        "provider_snapshot": provider_snapshot(provider),
        "mcp_server_snapshots": [
            mcp_server_snapshot(s) for s in (mcp_servers or [])
        ],
        "runtime": runtime_snapshot(),
    }


def make_run(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return {
        "id": data.get("id", new_id()),
        "name": data.get("name"),
        "status": data.get("status", "queued"),
        "kind": data.get("kind", "interactive"),
        "config_set_id": data["config_set_id"],
        "config_version_ids": data.get("config_version_ids", []),
        "task_id": data.get("task_id"),
        "eval_plan_id": data.get("eval_plan_id"),
        "schedule_id": data.get("schedule_id"),
        "chain_id": data.get("chain_id"),
        "parent_run_ids": data.get("parent_run_ids", []),
        "created_at": data.get("created_at", now),
        "started_at": data.get("started_at"),
        "completed_at": data.get("completed_at"),
        "created_by": data.get("created_by", "user"),
        "runtime": data.get("runtime", runtime_snapshot()),
        "summary": data.get("summary"),
    }


def make_run_input(run_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": data.get("id", new_id()),
        "run_id": run_id,
        "input_index": data["input_index"],
        "role": data.get("role", "user"),
        "content": data["content"],
        "test_case_id": data.get("test_case_id"),
        "source": data.get("source", {"type": "user"}),
        "created_at": data.get("created_at", utc_now()),
    }


def make_run_output(run_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": data.get("id", new_id()),
        "run_id": run_id,
        "config_version_id": data["config_version_id"],
        "slot_id": data["slot_id"],
        "provider_model_id": data["provider_model_id"],
        "response_index": data.get("response_index", 0),
        "status": data.get("status", "running"),
        "content": data.get("content", []),
        "text": data.get("text"),
        "error": data.get("error"),
        "usage": data.get("usage", {}),
        "raw_response_ref": data.get("raw_response_ref"),
        "tool_interactions": data.get("tool_interactions"),
        "created_at": data.get("created_at", utc_now()),
        "completed_at": data.get("completed_at"),
    }


def make_run_chain(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return {
        "id": data.get("id", new_id()),
        "name": data["name"],
        "root_run_id": data.get("root_run_id"),
        "created_at": data.get("created_at", now),
        "updated_at": data.get("updated_at", now),
        "archived": data.get("archived", False),
        "default_config_set_id": data.get("default_config_set_id"),
    }


def make_run_edge(chain_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": data.get("id", new_id()),
        "chain_id": chain_id,
        "parent_run_id": data["parent_run_id"],
        "child_run_id": data["child_run_id"],
        "mapping": data.get("mapping", {}),
        "created_at": data.get("created_at", utc_now()),
    }


def make_annotation(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return {
        "id": data.get("id", new_id()),
        "target": data["target"],
        "rating": data.get("rating"),
        "severity": data.get("severity"),
        "criteria_id": data.get("criteria_id"),
        "judge": data.get("judge", "human"),
        "comment": data.get("comment", ""),
        "created_at": data.get("created_at", now),
        "updated_at": data.get("updated_at", now),
    }


def make_artifact(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": data.get("id", new_id()),
        "run_id": data.get("run_id"),
        "output_id": data.get("output_id"),
        "kind": data["kind"],
        "modality": data["modality"],
        "mime_type": data["mime_type"],
        "filename": data["filename"],
        "path": data["path"],
        "size_bytes": data.get("size_bytes"),
        "sha256": data.get("sha256"),
        "created_at": data.get("created_at", utc_now()),
        "metadata": data.get("metadata", {}),
    }


def make_eval_plan(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return {
        "id": data.get("id", new_id()),
        "task_id": data.get("task_id"),
        "name": data["name"],
        "version": data.get("version", 1),
        "status": data.get("status", "draft"),
        "brief": data["brief"],
        "config_set_ids": data.get("config_set_ids", []),
        "prompt_set_ids": data.get("prompt_set_ids", []),
        "created_at": data.get("created_at", now),
        "updated_at": data.get("updated_at", now),
    }


def make_schedule(data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return {
        "id": data.get("id", new_id()),
        "task_id": data.get("task_id"),
        "eval_plan_id": data.get("eval_plan_id"),
        "config_set_id": data.get("config_set_id"),
        "name": data["name"],
        "status": data.get("status", "active"),
        "cadence": data.get("cadence", {"type": "manual"}),
        "model_discovery": data.get("model_discovery"),
        "created_at": data.get("created_at", now),
        "updated_at": data.get("updated_at", now),
        "last_run_id": data.get("last_run_id"),
    }
