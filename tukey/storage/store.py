"""JSONL/JSON file I/O and data directory management for ~/.tukey/"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_DATA_DIR = Path.home() / ".tukey"


class Storage:
    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self.chatrooms_dir = self.data_dir / "chatrooms"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chatrooms_dir.mkdir(exist_ok=True)

    def room_dir(self, room_id: str) -> Path:
        return self.chatrooms_dir / room_id

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

    # --- Room helpers ---

    def list_rooms(self) -> list[str]:
        if not self.chatrooms_dir.exists():
            return []
        return [
            d.name for d in sorted(self.chatrooms_dir.iterdir()) if d.is_dir()
        ]

    def read_room_meta(self, room_id: str) -> dict[str, Any]:
        return self.read_json(self.room_dir(room_id) / "meta.json")

    def write_room_meta(self, room_id: str, meta: dict[str, Any]) -> None:
        self.write_json(self.room_dir(room_id) / "meta.json", meta)

    def append_message(self, room_id: str, message: dict[str, Any]) -> None:
        self.append_jsonl(self.room_dir(room_id) / "messages.jsonl", message)

    def read_messages(self, room_id: str) -> list[dict[str, Any]]:
        return self.read_jsonl(self.room_dir(room_id) / "messages.jsonl")

    def delete_room(self, room_id: str) -> None:
        import shutil
        room = self.room_dir(room_id)
        if room.exists():
            shutil.rmtree(room)
