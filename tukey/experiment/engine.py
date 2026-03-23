"""Experiment engine: create experiments, run test cases, collect results."""

from __future__ import annotations

import asyncio
import sys
import time
import uuid
from datetime import datetime, timezone
from importlib.metadata import version as pkg_version
from typing import Any

import tukey
from tukey.config import ConfigManager
from tukey.providers.openai_provider import OpenAICompatibleProvider
from tukey.storage import Storage


class Experiment:
    def __init__(
        self,
        storage: Storage,
        config: ConfigManager,
        experiment_id: str | None = None,
    ):
        self.storage = storage
        self.config = config
        self.experiment_id = experiment_id or str(uuid.uuid4())

    # --- CRUD ---

    def create(self, name: str, chatroom_id: str, brief: dict[str, Any]) -> dict[str, Any]:
        self._validate_brief(brief)
        now = datetime.now(timezone.utc).isoformat()
        meta = {
            "id": self.experiment_id,
            "name": name,
            "version": 0,
            "status": "draft",
            "chatroom_id": chatroom_id,
            "brief": brief,
            "created_at": now,
            "updated_at": now,
        }
        self.storage.write_experiment_meta(self.experiment_id, meta)
        return meta

    def get_meta(self) -> dict[str, Any]:
        return self.storage.read_experiment_meta(self.experiment_id)

    def update_meta(self, updates: dict[str, Any]) -> dict[str, Any]:
        meta = self.get_meta()
        if "brief" in updates:
            self._validate_brief(updates["brief"])
        meta.update(updates)
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.storage.write_experiment_meta(self.experiment_id, meta)
        return meta

    def delete(self) -> None:
        self.storage.delete_experiment(self.experiment_id)

    # --- Test cases ---

    def add_test_cases(self, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for c in cases:
            tc = {
                "id": c.get("id", str(uuid.uuid4())),
                "turns": c["turns"],
                "expected_output": c.get("expected_output"),
                "tags": c.get("tags", []),
                "overrides": c.get("overrides", {}),
            }
            self.storage.append_test_case(self.experiment_id, tc)
            out.append(tc)
        return out

    def get_test_cases(self) -> list[dict[str, Any]]:
        return self.storage.read_test_cases(self.experiment_id)

    def replace_test_cases(self, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        for c in cases:
            normalized.append({
                "id": c.get("id", str(uuid.uuid4())),
                "turns": c["turns"],
                "expected_output": c.get("expected_output"),
                "tags": c.get("tags", []),
                "overrides": c.get("overrides", {}),
            })
        self.storage.write_test_cases(self.experiment_id, normalized)
        return normalized

    # --- Run ---

    async def run(self) -> dict[str, Any]:
        meta = self.get_meta()
        if meta.get("status") == "running":
            raise RuntimeError("Experiment is already running")
        brief = meta.get("brief")
        if not brief or not brief.get("decision"):
            raise ValueError("Brief with decision is required before running")
        test_cases = self.get_test_cases()
        if not test_cases:
            raise ValueError("At least one test case is required")

        chatroom_meta = self.storage.read_chatroom_meta(meta["chatroom_id"])
        if not chatroom_meta:
            raise ValueError(f"Chatroom {meta['chatroom_id']} not found")

        # Increment version, mark running
        meta["version"] = meta.get("version", 0) + 1
        meta["status"] = "running"
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.storage.write_experiment_meta(self.experiment_id, meta)

        models = chatroom_meta.get("models", [])
        run_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Snapshot providers
        providers_snapshot: dict[str, Any] = {}
        for m in models:
            pid = m.get("provider_id")
            if pid and pid not in providers_snapshot:
                prov = self.config.get_provider(pid)
                if prov:
                    providers_snapshot[pid] = {
                        "id": prov["id"],
                        "provider": prov.get("provider"),
                        "base_url": prov.get("base_url"),
                        "display_name": prov.get("display_name"),
                    }

        runtime = {
            "tukey_version": tukey.__version__,
            "httpx_version": pkg_version("httpx"),
            "python_version": sys.version,
        }

        run_meta = {
            "id": run_id,
            "experiment_id": self.experiment_id,
            "version": meta["version"],
            "status": "running",
            "models_snapshot": models,
            "providers_snapshot": providers_snapshot,
            "runtime": runtime,
            "created_at": now,
        }
        self.storage.write_run_meta(self.experiment_id, run_id, run_meta)

        # Execute all (test_case, model) pairs concurrently
        tasks = []
        for tc in test_cases:
            for model_cfg in models:
                tasks.append(self._execute_pair(run_id, tc, model_cfg, chatroom_meta))

        await asyncio.gather(*tasks, return_exceptions=True)

        # Mark complete
        run_meta["status"] = "complete"
        run_meta["completed_at"] = datetime.now(timezone.utc).isoformat()
        self.storage.write_run_meta(self.experiment_id, run_id, run_meta)

        meta["status"] = "complete"
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.storage.write_experiment_meta(self.experiment_id, meta)

        return run_meta

    async def _execute_pair(
        self, run_id: str, tc: dict, model_cfg: dict, chatroom_meta: dict
    ) -> None:
        """Execute a single (test_case, model) pair — sequential turns."""
        merged = self._merge_config(model_cfg, tc.get("overrides", {}))
        provider = self._build_provider(merged["provider_id"])
        conversation: list[dict] = []
        if merged.get("system_prompt"):
            conversation.append({"role": "system", "content": merged["system_prompt"]})

        exchanges: list[dict] = []
        error = False

        for turn in tc["turns"]:
            user_content = turn["content"] if isinstance(turn, dict) else turn
            conversation.append({"role": "user", "content": user_content})

            kwargs = self._build_completion_kwargs(merged)
            start = time.perf_counter()
            try:
                resp = await provider.complete(conversation, merged["model_id"], **kwargs)
                duration_ms = round((time.perf_counter() - start) * 1000, 1)
                conversation.append({"role": "assistant", "content": resp.content})
                exchanges.append({
                    "input": user_content,
                    "output": resp.content,
                    "tokens_in": resp.tokens_in,
                    "tokens_out": resp.tokens_out,
                    "cost": resp.cost,
                    "duration_ms": duration_ms,
                })
            except Exception as exc:
                duration_ms = round((time.perf_counter() - start) * 1000, 1)
                exchanges.append({
                    "input": user_content,
                    "output": str(exc),
                    "tokens_in": 0, "tokens_out": 0,
                    "cost": 0.0, "duration_ms": duration_ms,
                })
                error = True
                break

        result = {
            "id": str(uuid.uuid4()),
            "run_id": run_id,
            "test_case_id": tc["id"],
            "model_id": model_cfg["id"],
            "exchanges": exchanges,
            "total_tokens_in": sum(e["tokens_in"] for e in exchanges),
            "total_tokens_out": sum(e["tokens_out"] for e in exchanges),
            "total_cost": sum(e["cost"] for e in exchanges),
            "total_duration_ms": sum(e["duration_ms"] for e in exchanges),
            "error": error,
        }
        self.storage.append_result(self.experiment_id, run_id, result)

    # --- Runs ---

    def get_run(self, run_id: str) -> dict[str, Any]:
        return self.storage.read_run_meta(self.experiment_id, run_id)

    def list_runs(self) -> list[dict[str, Any]]:
        out = []
        for rid in self.storage.list_runs(self.experiment_id):
            meta = self.storage.read_run_meta(self.experiment_id, rid)
            if meta:
                out.append(meta)
        return out

    def get_results(self, run_id: str) -> list[dict[str, Any]]:
        return self.storage.read_results(self.experiment_id, run_id)

    # --- Annotations ---

    def add_annotation(self, run_id: str, annotation: dict[str, Any]) -> dict[str, Any]:
        if annotation.get("verdict") not in ("pass", "fail", "partial"):
            raise ValueError("verdict must be pass, fail, or partial")
        results = self.get_results(run_id)
        result_ids = {r["id"] for r in results}
        if annotation.get("result_id") and annotation["result_id"] not in result_ids:
            raise ValueError(f"Result {annotation['result_id']} not found in run {run_id}")
        ann = {
            "id": annotation.get("id", str(uuid.uuid4())),
            "result_id": annotation["result_id"],
            "judge": annotation.get("judge", "human"),
            "verdict": annotation["verdict"],
            "severity": annotation.get("severity"),
            "notes": annotation.get("notes"),
            "criteria_id": annotation.get("criteria_id"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.storage.append_annotation(self.experiment_id, run_id, ann)
        return ann

    def get_annotations(self, run_id: str) -> list[dict[str, Any]]:
        return self.storage.read_annotations(self.experiment_id, run_id)

    # --- Summary ---

    def get_run_summary(self, run_id: str) -> dict[str, Any]:
        results = self.get_results(run_id)
        annotations = self.get_annotations(run_id)
        ann_by_result: dict[str, list[dict]] = {}
        for a in annotations:
            ann_by_result.setdefault(a["result_id"], []).append(a)

        per_model: dict[str, dict[str, Any]] = {}
        for r in results:
            mid = r["model_id"]
            if mid not in per_model:
                per_model[mid] = {
                    "model_id": mid, "total": 0,
                    "pass": 0, "fail": 0, "partial": 0, "unannotated": 0,
                    "errors": 0, "total_cost": 0.0, "total_duration_ms": 0.0,
                }
            s = per_model[mid]
            s["total"] += 1
            s["total_cost"] += r.get("total_cost", 0)
            s["total_duration_ms"] += r.get("total_duration_ms", 0)
            if r.get("error"):
                s["errors"] += 1
            anns = ann_by_result.get(r["id"], [])
            if not anns:
                s["unannotated"] += 1
            else:
                for a in anns:
                    v = a.get("verdict")
                    if v in ("pass", "fail", "partial"):
                        s[v] += 1

        return {
            "run_id": run_id,
            "total_results": len(results),
            "total_annotations": len(annotations),
            "per_model": list(per_model.values()),
        }

    # --- Helpers ---

    def _build_provider(self, provider_id: str) -> OpenAICompatibleProvider:
        prov = self.config.get_provider(provider_id)
        if not prov:
            raise ValueError(f"Provider {provider_id} not found")
        return OpenAICompatibleProvider(
            api_key=prov.get("api_key"),
            base_url=prov.get("base_url"),
            provider_type=prov.get("provider"),
            strip_model_prefix=prov.get("strip_model_prefix", False),
        )

    @staticmethod
    def _merge_config(model_cfg: dict, overrides: dict) -> dict:
        merged = {**model_cfg}
        for key in ("system_prompt", "temperature", "max_tokens", "top_p",
                     "response_format", "tools", "tool_choice"):
            if key in overrides:
                merged[key] = overrides[key]
        return merged

    @staticmethod
    def _build_completion_kwargs(cfg: dict) -> dict:
        kwargs: dict[str, Any] = {}
        if cfg.get("temperature") is not None:
            kwargs["temperature"] = cfg["temperature"]
        if cfg.get("max_tokens") is not None:
            kwargs["max_tokens"] = cfg["max_tokens"]
        if cfg.get("top_p") is not None:
            kwargs["top_p"] = cfg["top_p"]
        if cfg.get("extra_params"):
            kwargs["extra_params"] = cfg["extra_params"]
        if cfg.get("response_format"):
            kwargs["response_format"] = cfg["response_format"]
        if cfg.get("tools"):
            kwargs["tools"] = cfg["tools"]
        if cfg.get("tool_choice") is not None:
            kwargs["tool_choice"] = cfg["tool_choice"]
        return kwargs

    @staticmethod
    def _validate_brief(brief: dict) -> None:
        if not isinstance(brief, dict) or not brief.get("decision"):
            raise ValueError("Brief must include a 'decision' field")
