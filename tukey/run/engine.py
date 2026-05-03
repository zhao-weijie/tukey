"""Run-native execution orchestration."""

from __future__ import annotations

import asyncio
from typing import Any

from tukey.config import ConfigManager
from tukey.core import contracts
from tukey.providers.base import LLMResponse
from tukey.run.executors import (
    ProviderFactory,
    TextCompletionExecutor,
    default_provider_factory,
    normalize_content_blocks,
    text_blocks_to_text,
)
from tukey.storage import Storage


class RunEngine:
    def __init__(
        self,
        storage: Storage,
        config: ConfigManager,
        *,
        provider_factory: ProviderFactory = default_provider_factory,
    ):
        self.storage = storage
        self.config = config
        self.provider_factory = provider_factory

    async def execute_run(
        self,
        run_id: str,
        *,
        inputs: list[dict[str, Any]] | None = None,
        n: int = 1,
        created_by: str = "system",
    ) -> dict[str, Any]:
        run = self.storage.read_run_record_meta(run_id)
        if not run:
            raise ValueError("Run not found")

        n = min(max(n, 1), 9)
        self._append_event(run_id, "run_started")
        self._set_run_status(run, "running", started=True)

        for input_record in inputs or []:
            data = dict(input_record)
            data["content"] = normalize_content_blocks(data.get("content"))
            data.setdefault("input_index", len(self.storage.read_run_inputs(run_id)))
            record = contracts.make_run_input(run_id, data)
            self.storage.append_run_input(run_id, record)

        recorded_input_ids = {
            event.get("data", {}).get("input_id")
            for event in self.storage.read_run_events(run_id)
            if event.get("type") == "input_recorded"
        }
        for input_record in self.storage.read_run_inputs(run_id):
            if input_record["id"] not in recorded_input_ids:
                self._append_event(run_id, "input_recorded", {"input_id": input_record["id"]})

        versions = self._ensure_config_versions(run, created_by=created_by)
        messages_by_version = {
            version["id"]: self._build_messages(run_id, version)
            for version in versions
        }

        tasks = []
        task_keys = []
        for version in versions:
            for response_index in range(n):
                tasks.append(
                    self._execute_one(version, messages_by_version[version["id"]], response_index)
                )
                task_keys.append((version, response_index))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        completed = 0
        failed = 0
        for index, result in enumerate(results):
            version, response_index = task_keys[index]
            if isinstance(result, Exception):
                output = self._failed_output(
                    run_id,
                    version,
                    response_index,
                    {
                        "type": result.__class__.__name__,
                        "message": str(result),
                    },
                )
                failed += 1
            else:
                output = self._complete_output(run_id, version, response_index, result)
                completed += 1
            self.storage.append_run_output(run_id, output)
            event_type = "output_completed" if output["status"] == "complete" else "output_failed"
            self._append_event(run_id, event_type, {"output_id": output["id"]})

        final_status = "complete" if completed else "failed"
        self._set_run_status(
            run,
            final_status,
            completed=True,
            summary={"complete_outputs": completed, "failed_outputs": failed},
        )
        self._append_event(
            run_id,
            "run_completed" if completed else "run_failed",
            {"complete_outputs": completed, "failed_outputs": failed},
        )
        return self.storage.read_run_record_meta(run_id)

    def _ensure_config_versions(
        self,
        run: dict[str, Any],
        *,
        created_by: str,
    ) -> list[dict[str, Any]]:
        config_set_id = run["config_set_id"]
        known_versions = {
            version["id"]: version
            for version in self.storage.read_config_versions(config_set_id)
        }
        if run.get("config_version_ids"):
            missing = [
                version_id
                for version_id in run["config_version_ids"]
                if version_id not in known_versions
            ]
            if missing:
                raise ValueError(f"Config versions not found: {missing}")
            return [known_versions[version_id] for version_id in run["config_version_ids"]]

        versions = []
        slots = self.storage.read_config_slots(config_set_id)
        for slot in slots:
            if not slot.get("enabled", True):
                continue
            provider = self.config.get_provider(slot["provider_id"])
            if not provider:
                raise ValueError(f"Provider not found: {slot['provider_id']}")
            mcp_servers = [
                self._require_mcp_server(server_id)
                for server_id in slot.get("mcp_server_ids") or []
            ]
            version = self.storage.freeze_config_version(
                config_set_id,
                slot,
                provider,
                mcp_servers,
                first_used_run_id=run["id"],
                created_by=created_by,
            )
            versions.append(version)
        run["config_version_ids"] = [version["id"] for version in versions]
        self.storage.write_run_record_meta(run["id"], run)
        return versions

    def _require_mcp_server(self, server_id: str) -> dict[str, Any]:
        server = self.config.get_mcp_server(server_id)
        if not server:
            raise ValueError(f"MCP server not found: {server_id}")
        return server

    async def _execute_one(
        self,
        version: dict[str, Any],
        messages: list[dict[str, Any]],
        response_index: int,
    ) -> LLMResponse:
        slot = version["slot_snapshot"]
        task_type = slot.get("task_type", "chat_completion")
        if task_type != "chat_completion":
            raise UnsupportedTaskTypeError(f"Unsupported task_type: {task_type}")
        provider_id = slot.get("provider_id")
        provider = self.config.get_provider(provider_id)
        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")
        executor = TextCompletionExecutor(self.provider_factory(provider))
        return await executor.execute(
            messages=messages,
            model=slot["provider_model_id"],
            slot_snapshot=slot,
        )

    def _build_messages(self, run_id: str, version: dict[str, Any]) -> list[dict[str, Any]]:
        slot = version["slot_snapshot"]
        messages: list[dict[str, Any]] = []
        if slot.get("system_prompt"):
            messages.append({"role": "system", "content": slot["system_prompt"]})
        for input_record in self.storage.read_run_inputs(run_id):
            messages.append({
                "role": input_record.get("role", "user"),
                "content": text_blocks_to_text(input_record.get("content", [])),
            })
        return messages

    def _complete_output(
        self,
        run_id: str,
        version: dict[str, Any],
        response_index: int,
        response: LLMResponse,
    ) -> dict[str, Any]:
        text = response.content or ""
        return contracts.make_run_output(run_id, {
            "config_version_id": version["id"],
            "slot_id": version["slot_id"],
            "provider_model_id": version["slot_snapshot"]["provider_model_id"],
            "response_index": response_index,
            "status": "complete",
            "content": [{"type": "text", "text": text}],
            "text": text,
            "usage": {
                "input_tokens": response.tokens_in,
                "output_tokens": response.tokens_out,
                "cost": response.cost,
                "duration_ms": response.duration_ms,
                "tokens_per_sec": response.tokens_per_sec,
            },
            "raw_response_ref": None,
            "completed_at": contracts.utc_now(),
        })

    def _failed_output(
        self,
        run_id: str,
        version: dict[str, Any],
        response_index: int,
        error: dict[str, Any],
    ) -> dict[str, Any]:
        return contracts.make_run_output(run_id, {
            "config_version_id": version["id"],
            "slot_id": version["slot_id"],
            "provider_model_id": version["slot_snapshot"]["provider_model_id"],
            "response_index": response_index,
            "status": "failed",
            "content": [],
            "error": error,
            "completed_at": contracts.utc_now(),
        })

    def _append_event(
        self,
        run_id: str,
        event_type: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.storage.append_run_event(run_id, {
            "id": contracts.new_id(),
            "run_id": run_id,
            "type": event_type,
            "data": data or {},
            "created_at": contracts.utc_now(),
        })

    def _set_run_status(
        self,
        run: dict[str, Any],
        status: str,
        *,
        started: bool = False,
        completed: bool = False,
        summary: dict[str, Any] | None = None,
    ) -> None:
        run["status"] = status
        if started and not run.get("started_at"):
            run["started_at"] = contracts.utc_now()
        if completed:
            run["completed_at"] = contracts.utc_now()
        if summary is not None:
            run["summary"] = summary
        self.storage.write_run_record_meta(run["id"], run)


class UnsupportedTaskTypeError(RuntimeError):
    pass
