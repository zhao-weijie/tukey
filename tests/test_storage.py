"""Tests for the storage module."""

from pathlib import Path

from tukey.core import contracts
from tukey.storage import Storage


def test_ensure_dirs(tmp_path: Path):
    s = Storage(tmp_path / "data")
    s.ensure_dirs()
    assert s.data_dir.exists()
    assert s.chatrooms_dir.exists()
    assert s.config_sets_dir.exists()
    assert s.run_records_dir.exists()
    assert s.run_chains_dir.exists()


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


def test_config_version_freeze_reuses_content_hash_and_strips_secrets(tmp_path: Path):
    s = Storage(tmp_path / "data")
    s.ensure_dirs()

    config_set = contracts.make_config_set({"id": "cs1", "name": "Baseline"})
    slot = contracts.make_config_slot("cs1", {
        "id": "slot1",
        "provider_id": "provider1",
        "provider_model_id": "openai/gpt-test",
        "display_name": "GPT Test",
        "temperature": 0.2,
    })
    provider = {
        "id": "provider1",
        "provider": "openai",
        "api_key": "sk-secret",
        "base_url": "https://example.test/v1",
        "display_name": "Gateway",
    }
    mcp_server = {
        "id": "mcp1",
        "name": "tools",
        "command": "node",
        "args": ["server.js"],
        "env": {"SECRET": "hidden"},
        "enabled": True,
    }

    s.write_config_set_meta("cs1", config_set)
    s.write_config_slots("cs1", [slot])
    first = s.freeze_config_version(
        "cs1", slot, provider, [mcp_server], first_used_run_id="run1"
    )
    second = s.freeze_config_version(
        "cs1", slot, provider, [mcp_server], first_used_run_id="run2"
    )

    assert first["id"] == second["id"]
    assert first["version"] == 1
    assert len(s.read_config_versions("cs1")) == 1
    assert "api_key" not in first["provider_snapshot"]
    assert "env" not in first["mcp_server_snapshots"][0]


def test_config_version_freeze_appends_when_slot_content_changes(tmp_path: Path):
    s = Storage(tmp_path / "data")
    s.ensure_dirs()
    slot = contracts.make_config_slot("cs1", {
        "id": "slot1",
        "provider_id": "provider1",
        "provider_model_id": "openai/gpt-test",
        "temperature": 0.2,
    })
    provider = {"id": "provider1", "provider": "openai", "api_key": "sk-secret"}

    first = s.freeze_config_version("cs1", slot, provider)
    changed = {**slot, "temperature": 0.7}
    second = s.freeze_config_version("cs1", changed, provider)

    assert first["id"] != second["id"]
    assert second["version"] == 2
    assert len(s.read_config_versions("cs1")) == 2


def test_run_outputs_append_for_retries(tmp_path: Path):
    s = Storage(tmp_path / "data")
    s.ensure_dirs()
    run = contracts.make_run({
        "id": "run1",
        "config_set_id": "cs1",
        "config_version_ids": ["cv1"],
    })
    first = contracts.make_run_output("run1", {
        "id": "out1",
        "config_version_id": "cv1",
        "slot_id": "slot1",
        "provider_model_id": "openai/gpt-test",
        "response_index": 0,
        "status": "failed",
        "text": "timeout",
        "error": {"message": "timeout", "retryable": True},
    })
    retry = contracts.make_run_output("run1", {
        "id": "out2",
        "config_version_id": "cv1",
        "slot_id": "slot1",
        "provider_model_id": "openai/gpt-test",
        "response_index": 1,
        "status": "complete",
        "text": "ok",
    })

    s.write_run_record_meta("run1", run)
    s.append_run_output("run1", first)
    s.append_run_output("run1", retry)

    outputs = s.read_run_outputs("run1")
    assert [o["id"] for o in outputs] == ["out1", "out2"]
    assert outputs[0]["status"] == "failed"
    assert outputs[1]["response_index"] == 1


def test_run_chain_edges_preserve_per_slot_lineage(tmp_path: Path):
    s = Storage(tmp_path / "data")
    s.ensure_dirs()
    chain = contracts.make_run_chain({"id": "chain1", "name": "Explore"})
    edge = contracts.make_run_edge("chain1", {
        "id": "edge1",
        "parent_run_id": "run1",
        "child_run_id": "run2",
        "mapping": {
            "slot1": {"output_id": "out1", "response_index": 0},
            "slot2": {"output_id": "out4", "response_index": 2},
        },
    })

    s.write_run_chain_meta("chain1", chain)
    s.append_run_edge("chain1", edge)

    edges = s.read_run_edges("chain1")
    assert len(edges) == 1
    assert edges[0]["parent_run_id"] == "run1"
    assert edges[0]["child_run_id"] == "run2"
    assert edges[0]["mapping"]["slot2"]["output_id"] == "out4"
