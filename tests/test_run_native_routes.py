"""Tests for run-native task and config-set REST routes."""


def _create_provider(client):
    r = client.post("/api/config/providers", json={
        "provider": "openai",
        "api_key": "sk-route-secret",
        "base_url": "https://example.test/v1",
        "display_name": "Route Provider",
    })
    assert r.status_code == 201
    return r.json()


def _create_config_set(client, name="Route Config Set"):
    r = client.post("/api/config-sets", json={
        "name": name,
        "description": "A route test config set",
        "tags": ["route"],
    })
    assert r.status_code == 201
    return r.json()


def _create_slot(client, config_set_id, provider_id, model="openai/test-model"):
    r = client.post(f"/api/config-sets/{config_set_id}/slots", json={
        "provider_id": provider_id,
        "provider_model_id": model,
        "display_name": "Test Model",
        "temperature": 0.2,
        "extra_params": {"seed": 1},
    })
    assert r.status_code == 201
    return r.json()


def test_task_crud_and_soft_delete(client):
    r = client.post("/api/tasks", json={
        "name": "Support triage",
        "description": "Choose a model for email triage",
        "tags": ["support", "triage"],
    })
    assert r.status_code == 201
    task = r.json()
    assert task["name"] == "Support triage"
    assert task["archived"] is False

    r = client.get("/api/tasks")
    assert r.status_code == 200
    assert any(item["id"] == task["id"] for item in r.json())

    r = client.patch(f"/api/tasks/{task['id']}", json={"name": "Support routing"})
    assert r.status_code == 200
    assert r.json()["name"] == "Support routing"

    r = client.delete(f"/api/tasks/{task['id']}")
    assert r.status_code == 204

    r = client.get(f"/api/tasks/{task['id']}")
    assert r.status_code == 200
    assert r.json()["archived"] is True


def test_task_default_config_set_validation(client):
    r = client.post("/api/tasks", json={
        "name": "Broken task",
        "default_config_set_id": "missing",
    })
    assert r.status_code == 422


def test_config_set_crud_slot_order_and_soft_delete(client):
    provider = _create_provider(client)
    config_set = _create_config_set(client)

    first = _create_slot(client, config_set["id"], provider["id"], "openai/first")
    second = _create_slot(client, config_set["id"], provider["id"], "openai/second")

    r = client.get(f"/api/config-sets/{config_set['id']}")
    assert r.status_code == 200
    assert r.json()["slot_order"] == [first["id"], second["id"]]

    r = client.patch(
        f"/api/config-sets/{config_set['id']}/slots/{second['id']}",
        json={"temperature": 0.7},
    )
    assert r.status_code == 200
    assert r.json()["temperature"] == 0.7

    r = client.delete(f"/api/config-sets/{config_set['id']}/slots/{first['id']}")
    assert r.status_code == 204

    r = client.get(f"/api/config-sets/{config_set['id']}/slots")
    assert r.status_code == 200
    slots = {slot["id"]: slot for slot in r.json()}
    assert slots[first["id"]]["enabled"] is False
    assert slots[second["id"]]["enabled"] is True

    r = client.get(f"/api/config-sets/{config_set['id']}")
    assert r.status_code == 200
    assert r.json()["slot_order"] == [second["id"]]

    r = client.delete(f"/api/config-sets/{config_set['id']}")
    assert r.status_code == 204
    r = client.get(f"/api/config-sets/{config_set['id']}")
    assert r.status_code == 200
    assert r.json()["archived"] is True


def test_config_slot_requires_existing_provider(client):
    config_set = _create_config_set(client)
    r = client.post(f"/api/config-sets/{config_set['id']}/slots", json={
        "provider_id": "missing-provider",
        "provider_model_id": "openai/test",
    })
    assert r.status_code == 422


def test_config_version_freeze_reuses_hash_and_strips_secrets(client):
    provider = _create_provider(client)
    config_set = _create_config_set(client)
    slot = _create_slot(client, config_set["id"], provider["id"])

    r = client.post(f"/api/config-sets/{config_set['id']}/versions:freeze", json={
        "slot_id": slot["id"],
        "first_used_run_id": "run-route-1",
        "created_by": "agent",
    })
    assert r.status_code == 201
    first = r.json()
    assert first["slot_id"] == slot["id"]
    assert first["version"] == 1
    assert first["created_by"] == "agent"
    assert "api_key" not in first["provider_snapshot"]

    r = client.post(f"/api/config-sets/{config_set['id']}/versions:freeze", json={
        "slot_id": slot["id"],
        "first_used_run_id": "run-route-2",
    })
    assert r.status_code == 201
    second = r.json()
    assert second["id"] == first["id"]

    r = client.get(f"/api/config-sets/{config_set['id']}/versions")
    assert r.status_code == 200
    versions = r.json()
    assert len(versions) == 1
    assert versions[0]["content_hash"] == first["content_hash"]


def test_config_version_freeze_404s_for_missing_slot(client):
    config_set = _create_config_set(client)
    r = client.post(f"/api/config-sets/{config_set['id']}/versions:freeze", json={
        "slot_id": "missing-slot",
    })
    assert r.status_code == 404
