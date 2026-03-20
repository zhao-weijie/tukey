"""JSONL/JSON file I/O and data directory management for ~/.tukey/"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


DEFAULT_DATA_DIR = Path.home() / ".tukey"


class Storage:
    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self.chatrooms_dir = self.data_dir / "chatrooms"
        self.experiments_dir = self.data_dir / "experiments"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chatrooms_dir.mkdir(exist_ok=True)
        self.experiments_dir.mkdir(exist_ok=True)

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
