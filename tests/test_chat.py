"""Tests for the chat module and server routes."""

from tukey.chat.room import ChatRoom


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


def test_chat_create_and_snapshot(storage, config):
    room = ChatRoom(storage, config)
    providers = config.list_providers()
    room.create("Room", models=[{
        "provider_id": providers[0]["id"],
        "model_id": "gpt-4",
        "display_name": "GPT-4",
    }])
    chat = room.create_chat("First Chat")
    assert chat["name"] == "First Chat"
    assert len(chat["models_snapshot"]) == 1
    assert chat["models_snapshot"][0]["model_id"] == "gpt-4"


def test_chat_messages_empty(storage, config):
    room = ChatRoom(storage, config)
    room.create("Room")
    chat = room.create_chat()
    assert room.get_messages(chat["id"]) == []


def test_list_chats(storage, config):
    room = ChatRoom(storage, config)
    room.create("Room")
    room.create_chat("Chat A")
    room.create_chat("Chat B")
    chats = room.list_chats()
    assert len(chats) == 2


# --- API route tests ---

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_api_create_and_list_chatrooms(client):
    r = client.post("/api/chat/chatrooms", json={"name": "Room 1"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Room 1"
    cr_id = data["id"]

    r = client.get("/api/chat/chatrooms")
    assert r.status_code == 200
    assert any(c["id"] == cr_id for c in r.json())


def test_api_get_chatroom(client):
    r = client.post("/api/chat/chatrooms", json={"name": "Room X"})
    cr_id = r.json()["id"]

    r = client.get(f"/api/chat/chatrooms/{cr_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "Room X"


def test_api_update_chatroom(client):
    r = client.post("/api/chat/chatrooms", json={"name": "Old"})
    cr_id = r.json()["id"]

    r = client.patch(f"/api/chat/chatrooms/{cr_id}", json={"name": "New"})
    assert r.status_code == 200
    assert r.json()["name"] == "New"


def test_api_delete_chatroom(client):
    r = client.post("/api/chat/chatrooms", json={"name": "Doomed"})
    cr_id = r.json()["id"]

    r = client.delete(f"/api/chat/chatrooms/{cr_id}")
    assert r.status_code == 204

    r = client.get(f"/api/chat/chatrooms/{cr_id}")
    assert r.status_code == 404


# --- Reproducibility snapshot tests ---

def test_chat_create_snapshots_providers(storage, config):
    room = ChatRoom(storage, config)
    providers = config.list_providers()
    pid = providers[0]["id"]
    room.create("Room", models=[{
        "provider_id": pid,
        "model_id": "gpt-4",
        "display_name": "GPT-4",
    }])
    chat = room.create_chat("Snap Chat")

    # providers_snapshot present and keyed by provider_id
    assert "providers_snapshot" in chat
    assert pid in chat["providers_snapshot"]
    snap = chat["providers_snapshot"][pid]
    assert snap["id"] == pid
    assert "api_key" not in snap  # must be stripped

    # runtime present
    assert "runtime" in chat
    rt = chat["runtime"]
    assert "tukey_version" in rt
    assert "litellm_version" in rt
    assert "python_version" in rt


# --- Search tests ---

def _setup_chatroom_with_message(client, room_name="SearchRoom", msg_content="hello world"):
    r = client.post("/api/chat/chatrooms", json={"name": room_name})
    cr = r.json()
    r = client.post(f"/api/chat/chatrooms/{cr['id']}/chats", json={"name": "Chat1"})
    chat = r.json()
    # Write a message directly via storage since send_message needs a real provider
    from tukey.server.routes.chat import _storage
    _storage.append_chat_message(cr["id"], chat["id"], {
        "id": "msg1", "role": "user", "content": msg_content,
        "created_at": "2024-01-01T00:00:00Z",
        "responses": [{"model_id": "m1", "content": "response text about bananas"}],
    })
    return cr, chat


def test_search_chatroom_name(client):
    _setup_chatroom_with_message(client, room_name="UniqueAlpha")
    r = client.get("/api/search?q=UniqueAlpha")
    assert r.status_code == 200
    results = r.json()["results"]
    assert any(r["type"] == "chatroom" and r["chatroom_name"] == "UniqueAlpha" for r in results)


def test_search_message_content(client):
    _setup_chatroom_with_message(client, msg_content="quantum entanglement discussion")
    r = client.get("/api/search?q=quantum")
    assert r.status_code == 200
    results = r.json()["results"]
    assert any(r["match"] == "message_content" for r in results)


def test_search_response_content(client):
    _setup_chatroom_with_message(client)
    r = client.get("/api/search?q=bananas")
    assert r.status_code == 200
    results = r.json()["results"]
    assert any(r["match"] == "response_content" for r in results)


# --- Export / Import tests ---

def test_export_import_roundtrip(client):
    # Create a chatroom with a chat and message
    cr, chat = _setup_chatroom_with_message(client, room_name="ExportMe", msg_content="export test msg")

    # Export
    r = client.get(f"/api/chat/chatrooms/{cr['id']}/export")
    assert r.status_code == 200
    export_data = r.json()
    assert export_data["tukey_export"]["version"] == 1
    assert export_data["chatroom"]["name"] == "ExportMe"
    assert len(export_data["chats"]) == 1
    assert len(export_data["chats"][0]["messages"]) == 1

    # Import
    r = client.post("/api/chat/chatrooms/import", json={"data": export_data})
    assert r.status_code == 201
    imported = r.json()
    assert imported["name"] == "ExportMe"
    assert imported["id"] != cr["id"]  # fresh UUID

    # Verify imported chats exist
    r = client.get(f"/api/chat/chatrooms/{imported['id']}/chats")
    assert r.status_code == 200
    imported_chats = r.json()
    assert len(imported_chats) == 1
    assert imported_chats[0]["id"] != chat["id"]  # fresh UUID

    # Verify messages
    r = client.get(f"/api/chat/chatrooms/{imported['id']}/chats/{imported_chats[0]['id']}/messages")
    assert r.status_code == 200
    msgs = r.json()
    assert len(msgs) == 1
    assert msgs[0]["content"] == "export test msg"


# --- Manifest tests ---

def test_get_manifest(storage, config):
    room = ChatRoom(storage, config)
    providers = config.list_providers()
    pid = providers[0]["id"]
    room.create("Room", models=[{
        "provider_id": pid,
        "model_id": "gpt-4",
        "display_name": "GPT-4",
    }])
    chat = room.create_chat("Manifest Chat")
    # Write a message directly
    storage.append_chat_message(room.chatroom_id, chat["id"], {
        "id": "m1", "role": "user", "content": "hello",
        "created_at": "2024-01-01T00:00:00Z",
        "responses": [{"model_id": "gpt-4", "content": "hi", "tokens_in": 5, "tokens_out": 3, "cost": 0.001, "duration_ms": 200}],
    })
    manifest = room.get_manifest(chat["id"])
    assert manifest["chatroom"]["name"] == "Room"
    assert manifest["chat"]["id"] == chat["id"]
    assert manifest["chat"]["models_snapshot"][0]["model_id"] == "gpt-4"
    assert len(manifest["turns"]) == 1
    assert manifest["turns"][0]["content"] == "hello"
    assert manifest["turns"][0]["responses"][0]["tokens_in"] == 5
    assert manifest["turns"][0]["responses"][0].get("error") is False


def test_api_manifest(client):
    cr, chat = _setup_chatroom_with_message(client, room_name="ManifestRoom", msg_content="manifest test")
    r = client.get(f"/api/chat/chatrooms/{cr['id']}/chats/{chat['id']}/manifest")
    assert r.status_code == 200
    data = r.json()
    assert data["chatroom"]["name"] == "ManifestRoom"
    assert len(data["turns"]) == 1
    assert data["turns"][0]["content"] == "manifest test"


def test_api_manifest_404(client):
    r = client.get("/api/chat/chatrooms/nonexistent/chats/fake/manifest")
    assert r.status_code == 404


# --- Model config: response_format / tools / tool_choice ---

def test_model_config_new_fields_preserved(storage, config):
    room = ChatRoom(storage, config)
    providers = config.list_providers()
    meta = room.create("Room", models=[{
        "provider_id": providers[0]["id"],
        "model_id": "gpt-4",
        "display_name": "GPT-4",
        "response_format": {"type": "json_object"},
        "tools": [{"type": "function", "function": {"name": "get_weather", "parameters": {"type": "object"}}}],
        "tool_choice": "auto",
    }])
    m = meta["models"][0]
    assert m["response_format"] == {"type": "json_object"}
    assert m["tools"][0]["function"]["name"] == "get_weather"
    assert m["tool_choice"] == "auto"


def test_model_config_new_fields_in_snapshot(storage, config):
    room = ChatRoom(storage, config)
    providers = config.list_providers()
    room.create("Room", models=[{
        "provider_id": providers[0]["id"],
        "model_id": "gpt-4",
        "display_name": "GPT-4",
        "response_format": {"type": "json_schema", "json_schema": {"name": "test"}},
        "tools": [{"type": "function", "function": {"name": "search", "parameters": {}}}],
        "tool_choice": "required",
    }])
    chat = room.create_chat("Snap")
    snap = chat["models_snapshot"][0]
    assert snap["response_format"]["type"] == "json_schema"
    assert snap["tools"][0]["function"]["name"] == "search"
    assert snap["tool_choice"] == "required"


def test_model_config_new_fields_default_none(storage, config):
    room = ChatRoom(storage, config)
    providers = config.list_providers()
    meta = room.create("Room", models=[{
        "provider_id": providers[0]["id"],
        "model_id": "gpt-4",
    }])
    m = meta["models"][0]
    assert m["response_format"] is None
    assert m["tools"] is None
    assert m["tool_choice"] is None
