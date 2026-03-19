"""Tests for the TukeyClient SDK."""

import pytest
from fastapi.testclient import TestClient

from tukey.client import TukeyClient
from tukey.server.app import create_app


@pytest.fixture
def sdk_client(tmp_path):
    app = create_app(data_dir=str(tmp_path / "sdk_data"))
    http = TestClient(app)
    client = TukeyClient(http_client=http)
    yield client
    http.close()


def test_chatroom_crud(sdk_client):
    cr = sdk_client.create_chatroom("SDK Room")
    assert cr["name"] == "SDK Room"

    fetched = sdk_client.get_chatroom(cr["id"])
    assert fetched["name"] == "SDK Room"

    updated = sdk_client.update_chatroom(cr["id"], name="Updated")
    assert updated["name"] == "Updated"

    rooms = sdk_client.list_chatrooms()
    assert any(r["id"] == cr["id"] for r in rooms)

    sdk_client.delete_chatroom(cr["id"])
    from httpx import HTTPStatusError
    with pytest.raises(HTTPStatusError):
        sdk_client.get_chatroom(cr["id"])


def test_chat_crud(sdk_client):
    cr = sdk_client.create_chatroom("Chat CRUD Room")
    chat = sdk_client.create_chat(cr["id"], name="My Chat")
    assert chat["name"] == "My Chat"

    fetched = sdk_client.get_chat(cr["id"], chat["id"])
    assert fetched["id"] == chat["id"]

    chats = sdk_client.list_chats(cr["id"])
    assert len(chats) == 1

    sdk_client.delete_chat(cr["id"], chat["id"])
    from httpx import HTTPStatusError
    with pytest.raises(HTTPStatusError):
        sdk_client.get_chat(cr["id"], chat["id"])


def test_messages(sdk_client):
    cr = sdk_client.create_chatroom("Msg Room")
    chat = sdk_client.create_chat(cr["id"])
    msgs = sdk_client.get_messages(cr["id"], chat["id"])
    assert msgs == []


def test_manifest(sdk_client):
    cr = sdk_client.create_chatroom("Manifest Room")
    chat = sdk_client.create_chat(cr["id"])
    from tukey.server.routes.chat import _storage
    _storage.append_chat_message(cr["id"], chat["id"], {
        "id": "m1", "role": "user", "content": "test prompt",
        "created_at": "2024-01-01T00:00:00Z",
        "responses": [{"model_id": "x", "content": "reply", "tokens_in": 10, "tokens_out": 5}],
    })
    manifest = sdk_client.get_manifest(cr["id"], chat["id"])
    assert manifest["chatroom"]["name"] == "Manifest Room"
    assert len(manifest["turns"]) == 1
    assert manifest["turns"][0]["content"] == "test prompt"


def test_export_import(sdk_client):
    cr = sdk_client.create_chatroom("Export Room")
    sdk_client.create_chat(cr["id"], name="Chat1")
    data = sdk_client.export_chatroom(cr["id"])
    assert data["tukey_export"]["version"] == 1

    imported = sdk_client.import_chatroom(data)
    assert imported["name"] == "Export Room"
    assert imported["id"] != cr["id"]


def test_context_manager(tmp_path):
    app = create_app(data_dir=str(tmp_path / "ctx_data"))
    http = TestClient(app)
    with TukeyClient(http_client=http) as client:
        cr = client.create_chatroom("Context Room")
        assert cr["name"] == "Context Room"
