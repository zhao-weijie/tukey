"""Tests for the chat module and server routes."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tukey.storage import Storage
from tukey.config import ConfigManager
from tukey.chat.room import ChatRoom
from tukey.server.app import create_app


@pytest.fixture
def storage(tmp_path: Path):
    s = Storage(tmp_path / "data")
    s.ensure_dirs()
    return s


@pytest.fixture
def config(storage: Storage):
    cm = ConfigManager(storage)
    cm.add_provider("openai", "sk-test", base_url="http://localhost:9999")
    return cm


@pytest.fixture
def app(tmp_path: Path):
    return create_app(data_dir=str(tmp_path / "appdata"))


@pytest.fixture
def client(app):
    return TestClient(app)


def test_chatroom_create(storage, config):
    room = ChatRoom(storage, config)
    providers = config.list_providers()
    meta = room.create("Test Room", models=[{
        "provider_id": providers[0]["id"],
        "model_id": "gpt-4",
        "display_name": "GPT-4",
    }])
    assert meta["name"] == "Test Room"
    assert len(meta["models"]) == 1
    assert meta["models"][0]["model_id"] == "gpt-4"


def test_chatroom_get_meta(storage, config):
    room = ChatRoom(storage, config)
    room.create("My Room")
    meta = room.get_meta()
    assert meta["name"] == "My Room"


def test_chatroom_update_meta(storage, config):
    room = ChatRoom(storage, config)
    room.create("Old Name")
    updated = room.update_meta({"name": "New Name"})
    assert updated["name"] == "New Name"


def test_chatroom_messages_empty(storage, config):
    room = ChatRoom(storage, config)
    room.create("Empty Room")
    assert room.get_messages() == []


# --- API route tests ---

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_api_create_and_list_rooms(client):
    r = client.post("/api/chat/rooms", json={"name": "Room 1"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Room 1"
    room_id = data["id"]

    r = client.get("/api/chat/rooms")
    assert r.status_code == 200
    rooms = r.json()
    assert any(rm["id"] == room_id for rm in rooms)


def test_api_get_room(client):
    r = client.post("/api/chat/rooms", json={"name": "Room X"})
    room_id = r.json()["id"]

    r = client.get(f"/api/chat/rooms/{room_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "Room X"


def test_api_update_room(client):
    r = client.post("/api/chat/rooms", json={"name": "Old"})
    room_id = r.json()["id"]

    r = client.patch(f"/api/chat/rooms/{room_id}", json={"name": "New"})
    assert r.status_code == 200
    assert r.json()["name"] == "New"


def test_api_delete_room(client):
    r = client.post("/api/chat/rooms", json={"name": "Doomed"})
    room_id = r.json()["id"]

    r = client.delete(f"/api/chat/rooms/{room_id}")
    assert r.status_code == 204

    r = client.get(f"/api/chat/rooms/{room_id}")
    assert r.status_code == 404


def test_api_get_messages_empty(client):
    r = client.post("/api/chat/rooms", json={"name": "Empty"})
    room_id = r.json()["id"]

    r = client.get(f"/api/chat/rooms/{room_id}/messages")
    assert r.status_code == 200
    assert r.json() == []


def test_api_room_not_found(client):
    assert client.get("/api/chat/rooms/nope").status_code == 404
    assert client.get("/api/chat/rooms/nope/messages").status_code == 404


def test_api_config_providers(client):
    r = client.get("/api/config/providers")
    assert r.status_code == 200
    assert r.json() == []

    r = client.post("/api/config/providers", json={
        "provider": "openai",
        "api_key": "sk-test",
    })
    assert r.status_code == 201
    pid = r.json()["id"]

    r = client.get("/api/config/providers")
    assert len(r.json()) == 1

    r = client.delete(f"/api/config/providers/{pid}")
    assert r.status_code == 204
