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


def _create_frozen_config_version(client):
    provider = _create_provider(client)
    config_set = _create_config_set(client)
    slot = _create_slot(client, config_set["id"], provider["id"])
    r = client.post(f"/api/config-sets/{config_set['id']}/versions:freeze", json={
        "slot_id": slot["id"],
        "first_used_run_id": "setup-run",
    })
    assert r.status_code == 201
    return config_set, slot, r.json()


def _create_run(client, status="queued"):
    config_set, slot, version = _create_frozen_config_version(client)
    r = client.post("/api/runs", json={
        "name": "Route Run",
        "status": status,
        "kind": "agent",
        "config_set_id": config_set["id"],
        "config_version_ids": [version["id"]],
    })
    assert r.status_code == 201
    return config_set, slot, version, r.json()


def _create_run_with_config(client, config_set, version, *, name="Route Run", chain_id=None):
    body = {
        "name": name,
        "status": "complete",
        "kind": "agent",
        "config_set_id": config_set["id"],
        "config_version_ids": [version["id"]],
    }
    if chain_id:
        body["chain_id"] = chain_id
    r = client.post("/api/runs", json=body)
    assert r.status_code == 201
    return r.json()


def _append_text_output(client, run, slot, version, text):
    r = client.post(f"/api/runs/{run['id']}/outputs", json={
        "config_version_id": version["id"],
        "slot_id": slot["id"],
        "provider_model_id": slot["provider_model_id"],
        "status": "complete",
        "text": text,
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


def test_provider_routes_redact_api_keys(client):
    r = client.post("/api/config/providers", json={
        "provider": "openrouter",
        "api_key": "sk-or-v1-1234567890abcdef",
        "base_url": "https://openrouter.ai/api/v1",
        "display_name": "OpenRouter",
    })
    assert r.status_code == 201
    provider = r.json()
    assert provider["api_key"] == "sk-or-...cdef"
    assert provider["api_key_present"] is True

    r = client.get("/api/config/providers")
    assert r.status_code == 200
    listed = r.json()
    assert listed[0]["id"] == provider["id"]
    assert listed[0]["api_key"] == "sk-or-...cdef"
    assert listed[0]["api_key_present"] is True

    r = client.get(f"/api/config/providers/{provider['id']}")
    assert r.status_code == 200
    assert r.json()["api_key"] == "sk-or-...cdef"

    r = client.patch(f"/api/config/providers/{provider['id']}", json={
        "api_key": "sk-or-v1-abcdef1234567890",
    })
    assert r.status_code == 200
    assert r.json()["api_key"] == "sk-or-...7890"

    stored = client.app.state.tukey.config.get_provider(provider["id"])
    assert stored["api_key"] == "sk-or-v1-abcdef1234567890"


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


def test_run_crud_inputs_outputs_events_and_summary(client):
    _, slot, version, run = _create_run(client)

    r = client.post(f"/api/runs/{run['id']}/inputs", json={
        "content": [{"type": "text", "text": "hello"}],
        "source": {"type": "agent", "ref_id": "case-1"},
    })
    assert r.status_code == 201
    assert r.json()["input_index"] == 0

    r = client.post(f"/api/runs/{run['id']}/outputs", json={
        "config_version_id": version["id"],
        "slot_id": slot["id"],
        "provider_model_id": slot["provider_model_id"],
        "response_index": 0,
        "status": "complete",
        "content": [{"type": "text", "text": "hi"}],
        "text": "hi",
        "usage": {"input_tokens": 3, "output_tokens": 2},
    })
    assert r.status_code == 201
    output = r.json()
    assert output["status"] == "complete"

    r = client.post(f"/api/runs/{run['id']}/events", json={
        "type": "output_completed",
        "data": {"output_id": output["id"]},
    })
    assert r.status_code == 201
    assert r.json()["type"] == "output_completed"

    r = client.patch(f"/api/runs/{run['id']}", json={"status": "complete"})
    assert r.status_code == 200
    assert r.json()["status"] == "complete"

    assert len(client.get(f"/api/runs/{run['id']}/inputs").json()) == 1
    assert len(client.get(f"/api/runs/{run['id']}/outputs").json()) == 1
    assert len(client.get(f"/api/runs/{run['id']}/events").json()) == 1

    r = client.get(f"/api/runs/{run['id']}/summary")
    assert r.status_code == 200
    summary = r.json()
    assert summary["total_inputs"] == 1
    assert summary["complete_outputs"] == 1


def test_run_rejects_output_for_non_member_config_version(client):
    _, slot, _, run = _create_run(client)
    r = client.post(f"/api/runs/{run['id']}/outputs", json={
        "config_version_id": "missing-version",
        "slot_id": slot["id"],
        "provider_model_id": slot["provider_model_id"],
    })
    assert r.status_code == 422


def test_run_output_validation_for_create_and_append_routes(client):
    config_set, slot, version, run = _create_run(client)
    valid_output = {
        "config_version_id": version["id"],
        "slot_id": slot["id"],
        "provider_model_id": slot["provider_model_id"],
        "status": "complete",
        "text": "validated",
    }
    invalid_cases = [
        {**valid_output, "config_version_id": "missing-version"},
        {**valid_output, "slot_id": "wrong-slot"},
        {**valid_output, "provider_model_id": "wrong-model"},
    ]

    for output in invalid_cases:
        r = client.post("/api/runs", json={
            "name": "Invalid Initial Output",
            "config_set_id": config_set["id"],
            "config_version_ids": [version["id"]],
            "outputs": [output],
        })
        assert r.status_code == 422

        r = client.post(f"/api/runs/{run['id']}/outputs", json=output)
        assert r.status_code == 422


def test_run_chain_edges_and_view_state(client):
    _, slot, version, parent = _create_run(client, status="complete")
    _, _, _, child = _create_run(client)
    r = client.post(f"/api/runs/{parent['id']}/outputs", json={
        "config_version_id": version["id"],
        "slot_id": slot["id"],
        "provider_model_id": slot["provider_model_id"],
        "status": "complete",
        "text": "parent output",
    })
    assert r.status_code == 201
    output = r.json()

    r = client.post("/api/run-chains", json={
        "name": "Route Chain",
        "root_run_id": parent["id"],
    })
    assert r.status_code == 201
    chain = r.json()

    r = client.post(f"/api/run-chains/{chain['id']}/edges", json={
        "parent_run_id": parent["id"],
        "child_run_id": child["id"],
        "mapping": {slot["id"]: {"output_id": output["id"], "response_index": 0}},
    })
    assert r.status_code == 201
    assert r.json()["mapping"][slot["id"]]["output_id"] == output["id"]

    r = client.put(f"/api/run-chains/{chain['id']}/view-state", json={
        "selected_outputs": {slot["id"]: output["id"]},
        "pinned_output_ids": [output["id"]],
        "collapsed_run_ids": [parent["id"]],
    })
    assert r.status_code == 200
    assert r.json()["selected_outputs"][slot["id"]] == output["id"]

    r = client.get(f"/api/run-chains/{chain['id']}/edges")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_run_chain_edge_requires_parent_output(client):
    _, _, _, parent = _create_run(client, status="complete")
    _, _, _, child = _create_run(client)
    chain = client.post("/api/run-chains", json={"name": "Bad Chain"}).json()
    r = client.post(f"/api/run-chains/{chain['id']}/edges", json={
        "parent_run_id": parent["id"],
        "child_run_id": child["id"],
        "mapping": {"slot": {"output_id": "missing-output", "response_index": 0}},
    })
    assert r.status_code == 422


def test_eval_plan_and_schedule_metadata_only(client):
    config_set = _create_config_set(client)
    task = client.post("/api/tasks", json={
        "name": "Eval task",
        "default_config_set_id": config_set["id"],
    }).json()

    r = client.post("/api/eval-plans", json={
        "task_id": task["id"],
        "name": "Plan 1",
        "brief": {"decision": "Choose the best support model"},
        "config_set_ids": [config_set["id"]],
    })
    assert r.status_code == 201
    plan = r.json()
    assert plan["status"] == "draft"

    r = client.post(f"/api/eval-plans/{plan['id']}/test-cases", json={
        "test_cases": [{"turns": [{"role": "user", "content": "hello"}], "tags": ["smoke"]}],
    })
    assert r.status_code == 201
    assert len(r.json()) == 1

    r = client.post("/api/schedules", json={
        "task_id": task["id"],
        "eval_plan_id": plan["id"],
        "config_set_id": config_set["id"],
        "name": "Manual schedule",
        "cadence": {"type": "manual"},
    })
    assert r.status_code == 201
    schedule = r.json()
    assert schedule["status"] == "active"

    r = client.delete(f"/api/schedules/{schedule['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/schedules/{schedule['id']}").json()["status"] == "paused"


def test_annotations_and_artifacts_target_run_outputs(client):
    _, slot, version, run = _create_run(client)
    output = client.post(f"/api/runs/{run['id']}/outputs", json={
        "config_version_id": version["id"],
        "slot_id": slot["id"],
        "provider_model_id": slot["provider_model_id"],
        "status": "complete",
        "text": "annotate me",
    }).json()

    r = client.post("/api/annotations", json={
        "target": {"type": "output", "run_id": run["id"], "output_id": output["id"]},
        "rating": "positive",
        "judge": "human",
        "comment": "good",
    })
    assert r.status_code == 201
    annotation = r.json()

    r = client.get(f"/api/annotations?run_id={run['id']}&output_id={output['id']}")
    assert r.status_code == 200
    assert [a["id"] for a in r.json()] == [annotation["id"]]

    r = client.patch(f"/api/annotations/{annotation['id']}", json={"comment": "great"})
    assert r.status_code == 200
    assert r.json()["comment"] == "great"

    r = client.post("/api/artifacts", json={
        "run_id": run["id"],
        "output_id": output["id"],
        "kind": "output",
        "modality": "image",
        "mime_type": "image/png",
        "filename": "result.png",
        "path": "runs/run/artifacts/result.png",
        "size_bytes": 42,
        "sha256": "abc123",
    })
    assert r.status_code == 201
    artifact = r.json()

    r = client.get(f"/api/artifacts/{artifact['id']}")
    assert r.status_code == 200
    assert r.json()["filename"] == "result.png"

    r = client.get(f"/api/runs/{run['id']}/artifacts")
    assert r.status_code == 200
    assert [a["id"] for a in r.json()] == [artifact["id"]]


def test_run_native_quick_setup_creates_task_config_set_and_chain(client):
    r = client.post("/api/config/quick-setup", json={
        "api_key": "sk-quick",
        "provider": "openai",
        "base_url": "https://example.test/v1",
        "display_name": "Quick Provider",
        "chatroom_name": "Quick Comparison",
        "models": [{"model_id": "openai/test-model", "display_name": "Test Model"}],
    })
    assert r.status_code == 201
    data = r.json()
    assert data["provider"]["api_key"] == "********"
    assert data["provider"]["api_key_present"] is True
    assert data["config_set"]["name"] == "Quick Comparison"
    assert data["slots"][0]["provider_id"] == data["provider"]["id"]
    assert data["task"]["default_config_set_id"] == data["config_set"]["id"]
    assert data["chain"]["default_config_set_id"] == data["config_set"]["id"]

    versions = client.get(f"/api/config-sets/{data['config_set']['id']}/versions").json()
    assert versions == []


def test_run_chain_detail_export_and_search_are_run_native(client):
    config_set, slot, version, run = _create_run(client, status="complete")
    input_record = client.post(f"/api/runs/{run['id']}/inputs", json={
        "content": [{"type": "text", "text": "find the best haiku"}],
    }).json()
    output = client.post(f"/api/runs/{run['id']}/outputs", json={
        "config_version_id": version["id"],
        "slot_id": slot["id"],
        "provider_model_id": slot["provider_model_id"],
        "status": "complete",
        "text": "frog pond benchmark",
    }).json()
    annotation = client.post("/api/annotations", json={
        "target": {"type": "output", "run_id": run["id"], "output_id": output["id"]},
        "rating": "positive",
        "comment": "memorable imagery",
    }).json()
    chain = client.post("/api/run-chains", json={
        "name": "Poetry Chain",
        "root_run_id": run["id"],
        "default_config_set_id": config_set["id"],
    }).json()
    client.patch(f"/api/runs/{run['id']}", json={"status": "complete"})

    detail = client.get(f"/api/run-chains/{chain['id']}/detail").json()
    assert detail["chain"]["id"] == chain["id"]
    assert detail["runs"][0]["id"] == run["id"]
    assert detail["inputs"][run["id"]][0]["id"] == input_record["id"]
    assert detail["outputs"][run["id"]][0]["id"] == output["id"]
    assert detail["annotations"][run["id"]][0]["id"] == annotation["id"]
    assert detail["config_versions"][config_set["id"]][0]["id"] == version["id"]

    exported = client.post(f"/api/run-chains/{chain['id']}/export").json()
    assert exported["kind"] == "tukey.run_chain_export"
    assert exported["chain"]["id"] == chain["id"]

    results = client.get("/api/search?q=frog").json()["results"]
    assert any(
        result["type"] == "run_output"
        and result["run_id"] == run["id"]
        and result["chain_id"] == chain["id"]
        for result in results
    )
    results = client.get("/api/search?q=memorable").json()["results"]
    assert any(
        result["type"] == "annotation"
        and result["annotation_id"] == annotation["id"]
        and result["chain_id"] == chain["id"]
        for result in results
    )


def test_search_derives_chain_contexts_from_all_membership_sources(client):
    config_set, slot, version = _create_frozen_config_version(client)
    direct_chain = client.post("/api/run-chains", json={"name": "Direct Chain"}).json()
    root_chain = client.post("/api/run-chains", json={"name": "Root Chain"}).json()
    edge_chain = client.post("/api/run-chains", json={"name": "Edge Chain"}).json()
    multi_chain = client.post("/api/run-chains", json={"name": "Multi Chain"}).json()

    direct = _create_run_with_config(
        client,
        config_set,
        version,
        name="direct-context",
        chain_id=direct_chain["id"],
    )
    root = _create_run_with_config(client, config_set, version, name="root-context")
    parent = _create_run_with_config(client, config_set, version, name="edge-parent")
    edge_child = _create_run_with_config(client, config_set, version, name="edge-child")
    multi = _create_run_with_config(client, config_set, version, name="multi-context")

    direct_output = _append_text_output(client, direct, slot, version, "direct constellation")
    root_output = _append_text_output(client, root, slot, version, "root constellation")
    edge_output = _append_text_output(client, edge_child, slot, version, "edge constellation")
    multi_output = _append_text_output(client, multi, slot, version, "multi constellation")

    client.patch(f"/api/run-chains/{root_chain['id']}", json={"root_run_id": root["id"]})
    client.post(f"/api/run-chains/{edge_chain['id']}/edges", json={
        "parent_run_id": parent["id"],
        "child_run_id": edge_child["id"],
        "mapping": {},
    })
    client.patch(f"/api/run-chains/{multi_chain['id']}", json={"root_run_id": multi["id"]})
    client.post(f"/api/run-chains/{edge_chain['id']}/edges", json={
        "parent_run_id": parent["id"],
        "child_run_id": multi["id"],
        "mapping": {},
    })

    results = client.get("/api/search?q=constellation&limit=20").json()["results"]
    contexts_by_output = {}
    for result in results:
        if result["type"] == "run_output":
            contexts_by_output.setdefault(result["output_id"], set()).add(result["chain_id"])

    assert contexts_by_output[direct_output["id"]] == {direct_chain["id"]}
    assert contexts_by_output[root_output["id"]] == {root_chain["id"]}
    assert contexts_by_output[edge_output["id"]] == {edge_chain["id"]}
    assert contexts_by_output[multi_output["id"]] == {
        edge_chain["id"],
        multi_chain["id"],
    }


def test_search_omits_run_matches_without_visible_chain_context(client):
    config_set, slot, version = _create_frozen_config_version(client)
    archived = _create_run_with_config(client, config_set, version, name="archived-context")
    no_chain = _create_run_with_config(client, config_set, version, name="no-chain-context")
    archived_output = _append_text_output(client, archived, slot, version, "hidden meteor")
    no_chain_output = _append_text_output(client, no_chain, slot, version, "hidden meteor")
    chain = client.post("/api/run-chains", json={
        "name": "Archived Chain",
        "root_run_id": archived["id"],
    }).json()
    client.patch(f"/api/run-chains/{chain['id']}", json={"archived": True})

    results = client.get("/api/search?q=hidden%20meteor").json()["results"]
    output_ids = {
        result.get("output_id")
        for result in results
        if result["type"] == "run_output"
    }
    assert archived_output["id"] not in output_ids
    assert no_chain_output["id"] not in output_ids
