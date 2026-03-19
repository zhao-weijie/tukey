"""Tests for the storage module."""

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


def test_chatroom_operations(tmp_path: Path):
    s = Storage(tmp_path / "data")
    s.ensure_dirs()

    assert s.list_chatrooms() == []

    meta = {"id": "cr1", "name": "Test Chatroom", "models": []}
    s.write_chatroom_meta("cr1", meta)
    assert s.list_chatrooms() == ["cr1"]
    assert s.read_chatroom_meta("cr1") == meta

    s.delete_chatroom("cr1")
    assert s.list_chatrooms() == []


def test_chat_operations(tmp_path: Path):
    s = Storage(tmp_path / "data")
    s.ensure_dirs()

    s.write_chatroom_meta("cr1", {"id": "cr1", "name": "Room", "models": []})
    assert s.list_chats("cr1") == []

    chat_meta = {"id": "ch1", "name": "Chat 1", "models_snapshot": []}
    s.write_chat_meta("cr1", "ch1", chat_meta)
    assert s.list_chats("cr1") == ["ch1"]
    assert s.read_chat_meta("cr1", "ch1") == chat_meta

    s.append_chat_message("cr1", "ch1", {"id": "m1", "content": "hi"})
    s.append_chat_message("cr1", "ch1", {"id": "m2", "content": "bye"})
    msgs = s.read_chat_messages("cr1", "ch1")
    assert len(msgs) == 2

    s.delete_chat("cr1", "ch1")
    assert s.list_chats("cr1") == []
