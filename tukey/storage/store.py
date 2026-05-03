"""JSONL/JSON file I/O and data directory management for ~/.tukey/"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from tukey.core import contracts


DEFAULT_DATA_DIR = Path.home() / ".tukey"
GLOBAL_CONFIG_PATH = Path.home() / ".tukey" / "tukey-global.json"


def read_global_config() -> dict:
    """Read global config (lives outside any data_dir, always at ~/.tukey/)."""
    if GLOBAL_CONFIG_PATH.exists():
        return json.loads(GLOBAL_CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def write_global_config(data: dict) -> None:
    """Write global config to ~/.tukey/tukey-global.json."""
    GLOBAL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    GLOBAL_CONFIG_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


class Storage:
    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self.chatrooms_dir = self.data_dir / "chatrooms"
        self.experiments_dir = self.data_dir / "experiments"
        self.tasks_dir = self.data_dir / "tasks"
        self.config_sets_dir = self.data_dir / "config_sets"
        self.eval_plans_dir = self.data_dir / "eval_plans"
        self.schedules_dir = self.data_dir / "schedules"
        self.run_records_dir = self.data_dir / "runs"
        self.run_chains_dir = self.data_dir / "run_chains"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chatrooms_dir.mkdir(exist_ok=True)
        self.experiments_dir.mkdir(exist_ok=True)
        self.tasks_dir.mkdir(exist_ok=True)
        self.config_sets_dir.mkdir(exist_ok=True)
        self.eval_plans_dir.mkdir(exist_ok=True)
        self.schedules_dir.mkdir(exist_ok=True)
        self.run_records_dir.mkdir(exist_ok=True)
        self.run_chains_dir.mkdir(exist_ok=True)

    @staticmethod
    def _list_dirs(path: Path) -> list[str]:
        if not path.exists():
            return []
        return [d.name for d in sorted(path.iterdir()) if d.is_dir()]

    def chatroom_dir(self, chatroom_id: str) -> Path:
        return self.chatrooms_dir / chatroom_id

    def chat_dir(self, chatroom_id: str, chat_id: str) -> Path:
        return self.chatroom_dir(chatroom_id) / "chats" / chat_id

    # --- JSON ---

    def read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    # --- JSONL ---

    def append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
        return records

    def write_jsonl(self, path: Path, records: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # --- Future run-native helpers ---

    def task_dir(self, task_id: str) -> Path:
        return self.tasks_dir / task_id

    def config_set_dir(self, config_set_id: str) -> Path:
        return self.config_sets_dir / config_set_id

    def eval_plan_dir(self, eval_plan_id: str) -> Path:
        return self.eval_plans_dir / eval_plan_id

    def schedule_dir(self, schedule_id: str) -> Path:
        return self.schedules_dir / schedule_id

    def run_record_dir(self, run_id: str) -> Path:
        return self.run_records_dir / run_id

    def run_chain_dir(self, chain_id: str) -> Path:
        return self.run_chains_dir / chain_id

    # --- Tasks ---

    def list_tasks(self) -> list[str]:
        return self._list_dirs(self.tasks_dir)

    def read_task_meta(self, task_id: str) -> dict[str, Any]:
        return self.read_json(self.task_dir(task_id) / "meta.json")

    def write_task_meta(self, task_id: str, meta: dict[str, Any]) -> None:
        self.write_json(self.task_dir(task_id) / "meta.json", meta)

    def delete_task(self, task_id: str) -> None:
        d = self.task_dir(task_id)
        if d.exists():
            shutil.rmtree(d)

    # --- Config sets ---

    def list_config_sets(self) -> list[str]:
        return self._list_dirs(self.config_sets_dir)

    def read_config_set_meta(self, config_set_id: str) -> dict[str, Any]:
        return self.read_json(self.config_set_dir(config_set_id) / "meta.json")

    def write_config_set_meta(self, config_set_id: str, meta: dict[str, Any]) -> None:
        self.write_json(self.config_set_dir(config_set_id) / "meta.json", meta)

    def delete_config_set(self, config_set_id: str) -> None:
        d = self.config_set_dir(config_set_id)
        if d.exists():
            shutil.rmtree(d)

    def read_config_slots(self, config_set_id: str) -> list[dict[str, Any]]:
        data = self.read_json(self.config_set_dir(config_set_id) / "slots.json")
        return data.get("slots", [])

    def write_config_slots(self, config_set_id: str, slots: list[dict[str, Any]]) -> None:
        self.write_json(self.config_set_dir(config_set_id) / "slots.json", {"slots": slots})

    def read_config_versions(self, config_set_id: str) -> list[dict[str, Any]]:
        return self.read_jsonl(self.config_set_dir(config_set_id) / "versions.jsonl")

    def append_config_version(self, config_set_id: str, version: dict[str, Any]) -> None:
        self.append_jsonl(self.config_set_dir(config_set_id) / "versions.jsonl", version)

    def freeze_config_version(
        self,
        config_set_id: str,
        slot_snapshot: dict[str, Any],
        provider: dict[str, Any] | None,
        mcp_servers: list[dict[str, Any]] | None = None,
        *,
        first_used_run_id: str | None = None,
        created_by: str = "system",
    ) -> dict[str, Any]:
        """Create or reuse an immutable config version for a slot snapshot."""
        content_hash = contracts.config_slot_content_hash(
            slot_snapshot, provider, mcp_servers
        )
        versions = self.read_config_versions(config_set_id)
        for version in versions:
            if version.get("content_hash") == content_hash:
                return version

        slot_id = slot_snapshot["id"]
        next_version = 1 + max(
            [
                v.get("version", 0)
                for v in versions
                if v.get("slot_id") == slot_id
            ],
            default=0,
        )
        version = contracts.make_config_version(
            config_set_id=config_set_id,
            slot_snapshot=slot_snapshot,
            provider=provider,
            mcp_servers=mcp_servers,
            version=next_version,
            first_used_run_id=first_used_run_id,
            created_by=created_by,
        )
        self.append_config_version(config_set_id, version)
        return version

    # --- Run records ---

    def list_run_records(self) -> list[str]:
        return self._list_dirs(self.run_records_dir)

    def read_run_record_meta(self, run_id: str) -> dict[str, Any]:
        return self.read_json(self.run_record_dir(run_id) / "meta.json")

    def write_run_record_meta(self, run_id: str, meta: dict[str, Any]) -> None:
        self.write_json(self.run_record_dir(run_id) / "meta.json", meta)

    def delete_run_record(self, run_id: str) -> None:
        d = self.run_record_dir(run_id)
        if d.exists():
            shutil.rmtree(d)

    def append_run_input(self, run_id: str, record: dict[str, Any]) -> None:
        self.append_jsonl(self.run_record_dir(run_id) / "inputs.jsonl", record)

    def read_run_inputs(self, run_id: str) -> list[dict[str, Any]]:
        return self.read_jsonl(self.run_record_dir(run_id) / "inputs.jsonl")

    def append_run_output(self, run_id: str, record: dict[str, Any]) -> None:
        self.append_jsonl(self.run_record_dir(run_id) / "outputs.jsonl", record)

    def read_run_outputs(self, run_id: str) -> list[dict[str, Any]]:
        return self.read_jsonl(self.run_record_dir(run_id) / "outputs.jsonl")

    def append_run_event(self, run_id: str, record: dict[str, Any]) -> None:
        self.append_jsonl(self.run_record_dir(run_id) / "events.jsonl", record)

    def read_run_events(self, run_id: str) -> list[dict[str, Any]]:
        return self.read_jsonl(self.run_record_dir(run_id) / "events.jsonl")

    def append_run_annotation(self, run_id: str, record: dict[str, Any]) -> None:
        self.append_jsonl(self.run_record_dir(run_id) / "annotations.jsonl", record)

    def read_run_annotations(self, run_id: str) -> list[dict[str, Any]]:
        return self.read_jsonl(self.run_record_dir(run_id) / "annotations.jsonl")

    def artifact_dir(self, run_id: str) -> Path:
        return self.run_record_dir(run_id) / "artifacts"

    # --- Run chains ---

    def list_run_chains(self) -> list[str]:
        return self._list_dirs(self.run_chains_dir)

    def read_run_chain_meta(self, chain_id: str) -> dict[str, Any]:
        return self.read_json(self.run_chain_dir(chain_id) / "meta.json")

    def write_run_chain_meta(self, chain_id: str, meta: dict[str, Any]) -> None:
        self.write_json(self.run_chain_dir(chain_id) / "meta.json", meta)

    def append_run_edge(self, chain_id: str, edge: dict[str, Any]) -> None:
        self.append_jsonl(self.run_chain_dir(chain_id) / "edges.jsonl", edge)

    def read_run_edges(self, chain_id: str) -> list[dict[str, Any]]:
        return self.read_jsonl(self.run_chain_dir(chain_id) / "edges.jsonl")

    def read_run_chain_view_state(self, chain_id: str) -> dict[str, Any]:
        data = self.read_json(self.run_chain_dir(chain_id) / "view_state.json")
        if data:
            return data
        return {
            "chain_id": chain_id,
            "selected_outputs": {},
            "pinned_output_ids": [],
            "collapsed_run_ids": [],
        }

    def write_run_chain_view_state(self, chain_id: str, state: dict[str, Any]) -> None:
        self.write_json(self.run_chain_dir(chain_id) / "view_state.json", state)

    # --- Eval plans ---

    def list_eval_plans(self) -> list[str]:
        return self._list_dirs(self.eval_plans_dir)

    def read_eval_plan_meta(self, eval_plan_id: str) -> dict[str, Any]:
        return self.read_json(self.eval_plan_dir(eval_plan_id) / "meta.json")

    def write_eval_plan_meta(self, eval_plan_id: str, meta: dict[str, Any]) -> None:
        self.write_json(self.eval_plan_dir(eval_plan_id) / "meta.json", meta)

    def append_eval_test_case(self, eval_plan_id: str, case: dict[str, Any]) -> None:
        self.append_jsonl(self.eval_plan_dir(eval_plan_id) / "test_cases.jsonl", case)

    def read_eval_test_cases(self, eval_plan_id: str) -> list[dict[str, Any]]:
        return self.read_jsonl(self.eval_plan_dir(eval_plan_id) / "test_cases.jsonl")

    def write_eval_test_cases(self, eval_plan_id: str, cases: list[dict[str, Any]]) -> None:
        self.write_jsonl(self.eval_plan_dir(eval_plan_id) / "test_cases.jsonl", cases)

    # --- Schedules ---

    def list_schedules(self) -> list[str]:
        return self._list_dirs(self.schedules_dir)

    def read_schedule_meta(self, schedule_id: str) -> dict[str, Any]:
        return self.read_json(self.schedule_dir(schedule_id) / "meta.json")

    def write_schedule_meta(self, schedule_id: str, meta: dict[str, Any]) -> None:
        self.write_json(self.schedule_dir(schedule_id) / "meta.json", meta)

    # --- Config shortcut ---

    @property
    def config_path(self) -> Path:
        return self.data_dir / "config.json"

    def read_config(self) -> dict[str, Any]:
        return self.read_json(self.config_path)

    def write_config(self, data: dict[str, Any]) -> None:
        self.ensure_dirs()
        self.write_json(self.config_path, data)

    # --- Chatroom helpers ---

    def list_chatrooms(self) -> list[str]:
        if not self.chatrooms_dir.exists():
            return []
        return [
            d.name for d in sorted(self.chatrooms_dir.iterdir()) if d.is_dir()
        ]

    def read_chatroom_meta(self, chatroom_id: str) -> dict[str, Any]:
        return self.read_json(self.chatroom_dir(chatroom_id) / "meta.json")

    def write_chatroom_meta(self, chatroom_id: str, meta: dict[str, Any]) -> None:
        self.write_json(self.chatroom_dir(chatroom_id) / "meta.json", meta)

    def delete_chatroom(self, chatroom_id: str) -> None:
        d = self.chatroom_dir(chatroom_id)
        if d.exists():
            shutil.rmtree(d)

    # --- Chat helpers ---

    def list_chats(self, chatroom_id: str) -> list[str]:
        chats_dir = self.chatroom_dir(chatroom_id) / "chats"
        if not chats_dir.exists():
            return []
        return [d.name for d in sorted(chats_dir.iterdir()) if d.is_dir()]

    def read_chat_meta(self, chatroom_id: str, chat_id: str) -> dict[str, Any]:
        return self.read_json(self.chat_dir(chatroom_id, chat_id) / "meta.json")

    def write_chat_meta(self, chatroom_id: str, chat_id: str, meta: dict[str, Any]) -> None:
        self.write_json(self.chat_dir(chatroom_id, chat_id) / "meta.json", meta)

    def delete_chat(self, chatroom_id: str, chat_id: str) -> None:
        d = self.chat_dir(chatroom_id, chat_id)
        if d.exists():
            shutil.rmtree(d)

    def append_chat_message(self, chatroom_id: str, chat_id: str, message: dict[str, Any]) -> None:
        self.append_jsonl(self.chat_dir(chatroom_id, chat_id) / "messages.jsonl", message)

    def read_chat_messages(self, chatroom_id: str, chat_id: str) -> list[dict[str, Any]]:
        return self.read_jsonl(self.chat_dir(chatroom_id, chat_id) / "messages.jsonl")

    def write_chat_messages(self, chatroom_id: str, chat_id: str, messages: list[dict[str, Any]]) -> None:
        self.write_jsonl(self.chat_dir(chatroom_id, chat_id) / "messages.jsonl", messages)

    # --- Chat annotation helpers ---

    def append_chat_annotation(self, chatroom_id: str, chat_id: str, annotation: dict[str, Any]) -> None:
        self.append_jsonl(self.chat_dir(chatroom_id, chat_id) / "annotations.jsonl", annotation)

    def read_chat_annotations(self, chatroom_id: str, chat_id: str) -> list[dict[str, Any]]:
        return self.read_jsonl(self.chat_dir(chatroom_id, chat_id) / "annotations.jsonl")

    def write_chat_annotations(self, chatroom_id: str, chat_id: str, annotations: list[dict[str, Any]]) -> None:
        self.write_jsonl(self.chat_dir(chatroom_id, chat_id) / "annotations.jsonl", annotations)

    # --- Experiment helpers ---

    def experiment_dir(self, experiment_id: str) -> Path:
        return self.experiments_dir / experiment_id

    def run_dir(self, experiment_id: str, run_id: str) -> Path:
        return self.experiment_dir(experiment_id) / "runs" / run_id

    def list_experiments(self) -> list[str]:
        if not self.experiments_dir.exists():
            return []
        return [d.name for d in sorted(self.experiments_dir.iterdir()) if d.is_dir()]

    def read_experiment_meta(self, experiment_id: str) -> dict[str, Any]:
        return self.read_json(self.experiment_dir(experiment_id) / "meta.json")

    def write_experiment_meta(self, experiment_id: str, meta: dict[str, Any]) -> None:
        self.write_json(self.experiment_dir(experiment_id) / "meta.json", meta)

    def delete_experiment(self, experiment_id: str) -> None:
        d = self.experiment_dir(experiment_id)
        if d.exists():
            shutil.rmtree(d)

    def read_test_cases(self, experiment_id: str) -> list[dict[str, Any]]:
        return self.read_jsonl(self.experiment_dir(experiment_id) / "test_cases.jsonl")

    def append_test_case(self, experiment_id: str, case: dict[str, Any]) -> None:
        self.append_jsonl(self.experiment_dir(experiment_id) / "test_cases.jsonl", case)

    def write_test_cases(self, experiment_id: str, cases: list[dict[str, Any]]) -> None:
        path = self.experiment_dir(experiment_id) / "test_cases.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases),
            encoding="utf-8",
        )

    def list_runs(self, experiment_id: str) -> list[str]:
        runs_dir = self.experiment_dir(experiment_id) / "runs"
        if not runs_dir.exists():
            return []
        return [d.name for d in sorted(runs_dir.iterdir()) if d.is_dir()]

    def read_run_meta(self, experiment_id: str, run_id: str) -> dict[str, Any]:
        return self.read_json(self.run_dir(experiment_id, run_id) / "meta.json")

    def write_run_meta(self, experiment_id: str, run_id: str, meta: dict[str, Any]) -> None:
        self.write_json(self.run_dir(experiment_id, run_id) / "meta.json", meta)

    def append_result(self, experiment_id: str, run_id: str, result: dict[str, Any]) -> None:
        self.append_jsonl(self.run_dir(experiment_id, run_id) / "results.jsonl", result)

    def read_results(self, experiment_id: str, run_id: str) -> list[dict[str, Any]]:
        return self.read_jsonl(self.run_dir(experiment_id, run_id) / "results.jsonl")

    def append_annotation(self, experiment_id: str, run_id: str, annotation: dict[str, Any]) -> None:
        self.append_jsonl(self.run_dir(experiment_id, run_id) / "annotations.jsonl", annotation)

    def read_annotations(self, experiment_id: str, run_id: str) -> list[dict[str, Any]]:
        return self.read_jsonl(self.run_dir(experiment_id, run_id) / "annotations.jsonl")
