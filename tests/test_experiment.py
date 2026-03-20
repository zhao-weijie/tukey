"""Tests for the experiment framework."""

import pytest

from tukey.chat.room import ChatRoom
from tukey.experiment.engine import Experiment


# --- Experiment CRUD ---

def test_experiment_create(storage, config):
    room = ChatRoom(storage, config)
    providers = config.list_providers()
    room.create("Room", models=[{
        "provider_id": providers[0]["id"],
        "model_id": "gpt-4",
    }])
    exp = Experiment(storage, config)
    meta = exp.create("My Experiment", room.chatroom_id, {
        "decision": "Test quality of responses",
        "criteria": [{"id": "c1", "name": "accuracy", "type": "binary", "description": "Is the answer correct?"}],
        "judges": ["human"],
    })
    assert meta["name"] == "My Experiment"
    assert meta["status"] == "draft"
    assert meta["version"] == 0
    assert meta["chatroom_id"] == room.chatroom_id
    assert meta["brief"]["decision"] == "Test quality of responses"


def test_experiment_create_requires_brief_decision(storage, config):
    room = ChatRoom(storage, config)
    room.create("Room")
    exp = Experiment(storage, config)
    with pytest.raises(ValueError, match="decision"):
        exp.create("Bad", room.chatroom_id, {"criteria": []})


def test_experiment_update_meta(storage, config):
    room = ChatRoom(storage, config)
    room.create("Room")
    exp = Experiment(storage, config)
    exp.create("Old", room.chatroom_id, {"decision": "test"})
    updated = exp.update_meta({"name": "New"})
    assert updated["name"] == "New"


def test_experiment_delete(storage, config):
    room = ChatRoom(storage, config)
    room.create("Room")
    exp = Experiment(storage, config)
    exp.create("Doomed", room.chatroom_id, {"decision": "test"})
    exp.delete()
    assert exp.get_meta() == {}


# --- Test cases ---

def test_add_and_get_test_cases(storage, config):
    room = ChatRoom(storage, config)
    room.create("Room")
    exp = Experiment(storage, config)
    exp.create("Exp", room.chatroom_id, {"decision": "test"})
    cases = exp.add_test_cases([
        {"turns": [{"role": "user", "content": "Hello"}]},
        {"turns": [{"role": "user", "content": "Hi"}, {"role": "user", "content": "Follow up"}]},
    ])
    assert len(cases) == 2
    assert cases[1]["turns"][1]["content"] == "Follow up"
    assert len(exp.get_test_cases()) == 2


def test_replace_test_cases(storage, config):
    room = ChatRoom(storage, config)
    room.create("Room")
    exp = Experiment(storage, config)
    exp.create("Exp", room.chatroom_id, {"decision": "test"})
    exp.add_test_cases([{"turns": [{"role": "user", "content": "old"}]}])
    replaced = exp.replace_test_cases([{"turns": [{"role": "user", "content": "new"}]}])
    assert len(replaced) == 1
    assert replaced[0]["turns"][0]["content"] == "new"
    assert len(exp.get_test_cases()) == 1


def test_test_case_overrides(storage, config):
    room = ChatRoom(storage, config)
    room.create("Room")
    exp = Experiment(storage, config)
    exp.create("Exp", room.chatroom_id, {"decision": "test"})
    cases = exp.add_test_cases([{
        "turns": [{"role": "user", "content": "test"}],
        "overrides": {"temperature": 0.0, "response_format": {"type": "json_object"}},
    }])
    assert cases[0]["overrides"]["temperature"] == 0.0
    assert cases[0]["overrides"]["response_format"]["type"] == "json_object"


# --- Annotation + Summary ---

def test_annotation_invalid_verdict(storage, config):
    room = ChatRoom(storage, config)
    room.create("Room")
    exp = Experiment(storage, config)
    exp.create("Exp", room.chatroom_id, {"decision": "test"})
    # Need a run first — but we can test verdict validation directly
    with pytest.raises(ValueError, match="verdict"):
        exp.add_annotation("fake-run", {"result_id": "r1", "verdict": "maybe"})


def test_merge_config():
    base = {"model_id": "gpt-4", "temperature": 1.0, "system_prompt": "hi", "provider_id": "p1"}
    overrides = {"temperature": 0.0, "system_prompt": "override", "response_format": {"type": "json_object"}}
    merged = Experiment._merge_config(base, overrides)
    assert merged["temperature"] == 0.0
    assert merged["system_prompt"] == "override"
    assert merged["response_format"] == {"type": "json_object"}
    assert merged["model_id"] == "gpt-4"


# --- API route tests ---

def _create_experiment_via_api(client):
    """Helper: create chatroom + experiment via API."""
    r = client.post("/api/chat/chatrooms", json={"name": "ExpRoom"})
    cr = r.json()
    r = client.post("/api/experiments", json={
        "name": "Test Exp",
        "chatroom_id": cr["id"],
        "brief": {"decision": "evaluate quality"},
    })
    assert r.status_code == 201
    return cr, r.json()


def test_api_create_experiment(client):
    _, exp = _create_experiment_via_api(client)
    assert exp["name"] == "Test Exp"
    assert exp["status"] == "draft"


def test_api_list_experiments(client):
    _create_experiment_via_api(client)
    r = client.get("/api/experiments")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_api_get_experiment(client):
    _, exp = _create_experiment_via_api(client)
    r = client.get(f"/api/experiments/{exp['id']}")
    assert r.status_code == 200
    assert r.json()["name"] == "Test Exp"


def test_api_update_experiment(client):
    _, exp = _create_experiment_via_api(client)
    r = client.patch(f"/api/experiments/{exp['id']}", json={"name": "Updated"})
    assert r.status_code == 200
    assert r.json()["name"] == "Updated"


def test_api_delete_experiment(client):
    _, exp = _create_experiment_via_api(client)
    r = client.delete(f"/api/experiments/{exp['id']}")
    assert r.status_code == 204
    r = client.get(f"/api/experiments/{exp['id']}")
    assert r.status_code == 404


def test_api_test_cases_crud(client):
    _, exp = _create_experiment_via_api(client)
    eid = exp["id"]

    # Add
    r = client.post(f"/api/experiments/{eid}/test-cases", json={
        "test_cases": [{"turns": [{"role": "user", "content": "hello"}]}],
    })
    assert r.status_code == 201
    assert len(r.json()) == 1

    # Get
    r = client.get(f"/api/experiments/{eid}/test-cases")
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Replace
    r = client.put(f"/api/experiments/{eid}/test-cases", json={
        "test_cases": [
            {"turns": [{"role": "user", "content": "a"}]},
            {"turns": [{"role": "user", "content": "b"}]},
        ],
    })
    assert r.status_code == 200
    assert len(r.json()) == 2

    r = client.get(f"/api/experiments/{eid}/test-cases")
    assert len(r.json()) == 2


def test_api_run_requires_test_cases(client):
    _, exp = _create_experiment_via_api(client)
    r = client.post(f"/api/experiments/{exp['id']}/run")
    assert r.status_code == 422


def test_api_experiment_not_found(client):
    r = client.get("/api/experiments/nonexistent")
    assert r.status_code == 404


def test_api_create_experiment_bad_chatroom(client):
    r = client.post("/api/experiments", json={
        "name": "Bad", "chatroom_id": "nope", "brief": {"decision": "test"},
    })
    assert r.status_code == 422
