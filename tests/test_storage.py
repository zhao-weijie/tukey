"""Tests for the storage module."""

import json
from pathlib import Path

from tukey.storage import Storage


def test_ensure_dirs(tmp_path: Path):
    s = Storage(tmp_path / "data")
    s.ensure_dirs()
    assert s.data_dir.exists()
    assert s.chatrooms_dir.exists()


def test_json_roundtrip(tmp_path: Path):
    s = Storage(tmp_path / "data")
    p = tmp_path / "data" / "test.json"
    data = {"key": "value", "nested": {"a": 1}}
    s.write_json(p, data)
    assert s.read_json(p) == data


def test_read_json_missing(tmp_path: Path):
    s = Storage(tmp_path / "data")
    assert s.read_json(tmp_path / "nope.json") == {}


def test_jsonl_roundtrip(tmp_path: Path):
    s = Storage(tmp_path / "data")
    p = tmp_path / "data" / "test.jsonl"
    s.append_jsonl(p, {"id": "1", "msg": "hello"})
    s.append_jsonl(p, {"id": "2", "msg": "world"})
    records = s.read_jsonl(p)
    assert len(records) == 2
    assert records[0]["msg"] == "hello"
    assert records[1]["msg"] == "world"


def test_read_jsonl_missing(tmp_path: Path):
    s = Storage(tmp_path / "data")
    assert s.read_jsonl(tmp_path / "nope.jsonl") == []


def test_config_roundtrip(tmp_path: Path):
    s = Storage(tmp_path / "data")
    cfg = {"providers": [{"id": "1", "provider": "openai"}]}
    s.write_config(cfg)
    assert s.read_config() == cfg


def test_room_operations(tmp_path: Path):
    s = Storage(tmp_path / "data")
    s.ensure_dirs()

    assert s.list_rooms() == []

    meta = {"id": "room1", "name": "Test Room"}
    s.write_room_meta("room1", meta)
    assert s.list_rooms() == ["room1"]
    assert s.read_room_meta("room1") == meta

    s.append_message("room1", {"id": "m1", "content": "hi"})
    s.append_message("room1", {"id": "m2", "content": "bye"})
    msgs = s.read_messages("room1")
    assert len(msgs) == 2

    s.delete_room("room1")
    assert s.list_rooms() == []
