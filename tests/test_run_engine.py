from __future__ import annotations

import pytest

from tukey.core import contracts
from tukey.providers.base import LLMResponse
from tukey.run import RunEngine


class MockTextProvider:
    def __init__(self, responses=None, error: Exception | None = None):
        self.responses = responses or []
        self.error = error
        self.calls = []

    async def complete(self, messages, model, **kwargs):
        self.calls.append({"messages": messages, "model": model, "kwargs": kwargs})
        if self.error:
            raise self.error
        index = len(self.calls) - 1
        content = self.responses[index] if index < len(self.responses) else f"response {index}"
        return LLMResponse(
            content=content,
            tokens_in=7,
            tokens_out=3,
            cost=0.001,
            duration_ms=10.0,
            tokens_per_sec=300.0,
            model=model,
        )


def _setup_config_set(storage, config, *, task_type="chat_completion"):
    provider = config.add_provider(
        "openai",
        "sk-engine-test",
        base_url="https://example.test/v1",
        display_name="Engine Provider",
    )
    config_set = contracts.make_config_set({"name": "Engine Set"})
    storage.write_config_set_meta(config_set["id"], config_set)
    slot = contracts.make_config_slot(config_set["id"], {
        "provider_id": provider["id"],
        "provider_model_id": "openai/test-model",
        "display_name": "Test Model",
        "system_prompt": "Be brief.",
        "temperature": 0.3,
        "task_type": task_type,
    })
    storage.write_config_slots(config_set["id"], [slot])
    config_set["slot_order"] = [slot["id"]]
    storage.write_config_set_meta(config_set["id"], config_set)
    return config_set, slot


def _create_run(storage, config_set_id, *, config_version_ids=None):
    run = contracts.make_run({
        "name": "Engine Run",
        "config_set_id": config_set_id,
        "config_version_ids": config_version_ids or [],
    })
    storage.write_run_record_meta(run["id"], run)
    storage.append_run_input(run["id"], contracts.make_run_input(run["id"], {
        "input_index": 0,
        "role": "user",
        "content": [{"type": "text", "text": "Hello"}],
    }))
    return run


@pytest.mark.asyncio
async def test_run_engine_mock_provider_success_writes_outputs_and_usage(storage, config):
    provider = MockTextProvider(["hi there"])
    config_set, slot = _setup_config_set(storage, config)
    run = _create_run(storage, config_set["id"])
    engine = RunEngine(storage, config, provider_factory=lambda _: provider)

    result = await engine.execute_run(run["id"])

    outputs = storage.read_run_outputs(run["id"])
    events = storage.read_run_events(run["id"])
    versions = storage.read_config_versions(config_set["id"])

    assert result["status"] == "complete"
    assert result["config_version_ids"] == [versions[0]["id"]]
    assert outputs[0]["status"] == "complete"
    assert outputs[0]["slot_id"] == slot["id"]
    assert outputs[0]["content"] == [{"type": "text", "text": "hi there"}]
    assert outputs[0]["text"] == "hi there"
    assert outputs[0]["usage"]["input_tokens"] == 7
    assert provider.calls[0]["messages"] == [
        {"role": "system", "content": "Be brief."},
        {"role": "user", "content": "Hello"},
    ]
    assert [event["type"] for event in events] == [
        "run_started",
        "input_recorded",
        "output_completed",
        "run_completed",
    ]


@pytest.mark.asyncio
async def test_run_engine_provider_failure_writes_failed_output(storage, config):
    provider = MockTextProvider(error=RuntimeError("provider down"))
    config_set, _ = _setup_config_set(storage, config)
    run = _create_run(storage, config_set["id"])
    engine = RunEngine(storage, config, provider_factory=lambda _: provider)

    result = await engine.execute_run(run["id"])

    outputs = storage.read_run_outputs(run["id"])
    assert result["status"] == "failed"
    assert outputs[0]["status"] == "failed"
    assert outputs[0]["error"]["message"] == "provider down"


@pytest.mark.asyncio
async def test_run_engine_executes_with_frozen_provider_settings_and_live_secret(storage, config):
    captured_providers = []
    config_set, slot = _setup_config_set(storage, config)
    config.update_provider(slot["provider_id"], {
        "api_key": "sk-before-freeze",
        "base_url": "https://frozen.test/v1",
        "strip_model_prefix": True,
    })
    version = storage.freeze_config_version(
        config_set["id"],
        slot,
        config.get_provider(slot["provider_id"]),
    )
    config.update_provider(slot["provider_id"], {
        "api_key": "sk-current-secret",
        "base_url": "https://changed.test/v1",
        "strip_model_prefix": False,
    })
    run = _create_run(storage, config_set["id"], config_version_ids=[version["id"]])

    def capture_provider(provider_config):
        captured_providers.append(provider_config)
        return MockTextProvider(["frozen provider ok"])

    engine = RunEngine(storage, config, provider_factory=capture_provider)

    await engine.execute_run(run["id"])

    assert captured_providers == [{
        "id": slot["provider_id"],
        "provider": "openai",
        "base_url": "https://frozen.test/v1",
        "display_name": "Engine Provider",
        "strip_model_prefix": True,
        "api_key": "sk-current-secret",
    }]


@pytest.mark.asyncio
async def test_run_engine_n_completions_and_retry_append_outputs(storage, config):
    provider = MockTextProvider(["a", "b", "retry"])
    config_set, _ = _setup_config_set(storage, config)
    run = _create_run(storage, config_set["id"])
    engine = RunEngine(storage, config, provider_factory=lambda _: provider)

    await engine.execute_run(run["id"], n=2)
    await engine.execute_run(run["id"], n=1)

    outputs = storage.read_run_outputs(run["id"])
    assert [output["response_index"] for output in outputs] == [0, 1, 0]
    assert [output["text"] for output in outputs] == ["a", "b", "retry"]


@pytest.mark.asyncio
async def test_run_engine_execute_body_normalizes_content_blocks(storage, config):
    provider = MockTextProvider(["ok"])
    config_set, _ = _setup_config_set(storage, config)
    run = contracts.make_run({"name": "Engine Run", "config_set_id": config_set["id"]})
    storage.write_run_record_meta(run["id"], run)
    engine = RunEngine(storage, config, provider_factory=lambda _: provider)

    await engine.execute_run(
        run["id"],
        inputs=[{"role": "user", "content": "Plain text input"}],
    )

    inputs = storage.read_run_inputs(run["id"])
    assert inputs[0]["content"] == [{"type": "text", "text": "Plain text input"}]
    assert provider.calls[0]["messages"][-1]["content"] == "Plain text input"


@pytest.mark.asyncio
async def test_run_engine_unsupported_task_type_creates_failed_output(storage, config):
    config_set, _ = _setup_config_set(storage, config, task_type="image_generation")
    run = _create_run(storage, config_set["id"])
    engine = RunEngine(storage, config, provider_factory=lambda _: MockTextProvider(["unused"]))

    result = await engine.execute_run(run["id"])

    outputs = storage.read_run_outputs(run["id"])
    assert result["status"] == "failed"
    assert outputs[0]["status"] == "failed"
    assert outputs[0]["error"]["type"] == "UnsupportedTaskTypeError"
    assert "image_generation" in outputs[0]["error"]["message"]


def test_execute_route_runs_existing_queued_run(client):
    provider = client.post("/api/config/providers", json={
        "provider": "openai",
        "api_key": "sk-route-engine",
        "base_url": "https://example.test/v1",
        "display_name": "Route Provider",
    }).json()
    config_set = client.post("/api/config-sets", json={"name": "Route Engine"}).json()
    slot = client.post(f"/api/config-sets/{config_set['id']}/slots", json={
        "provider_id": provider["id"],
        "provider_model_id": "openai/test-model",
        "task_type": "image_edit",
    }).json()
    run = client.post("/api/runs", json={
        "name": "Queued Route Run",
        "config_set_id": config_set["id"],
    }).json()

    r = client.post(f"/api/runs/{run['id']}/execute", json={
        "inputs": [{"content": [{"type": "text", "text": "hello"}]}],
    })

    assert r.status_code == 200
    assert r.json()["status"] == "failed"
    outputs = client.get(f"/api/runs/{run['id']}/outputs").json()
    assert outputs[0]["slot_id"] == slot["id"]
    assert outputs[0]["error"]["type"] == "UnsupportedTaskTypeError"
