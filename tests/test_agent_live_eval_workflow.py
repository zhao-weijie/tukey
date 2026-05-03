from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import httpx


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "tukey-live-eval"
    / "scripts"
    / "run_live_eval.py"
)

spec = importlib.util.spec_from_file_location("run_live_eval", SCRIPT_PATH)
run_live_eval = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["run_live_eval"] = run_live_eval
spec.loader.exec_module(run_live_eval)


def test_provider_guidance_and_exact_three_models():
    try:
        run_live_eval.pick_provider([], None)
    except SystemExit as exc:
        assert "OpenRouter" in str(exc)
        assert "does not collect provider secrets" in str(exc)
    else:
        raise AssertionError("Expected SystemExit")

    try:
        run_live_eval.require_three(["a", "b", "b"])
    except SystemExit as exc:
        assert "exactly three" in str(exc)
    else:
        raise AssertionError("Expected SystemExit")

    assert run_live_eval.require_three(["a", "b", "c"]) == ["a", "b", "c"]


def test_main_creates_public_api_records_and_prints_summary(capsys):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.method == "GET" and request.url.path == "/api/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.method == "GET" and request.url.path == "/api/config/providers":
            return httpx.Response(200, json=[{
                "id": "provider-1",
                "provider": "openrouter",
                "display_name": "OpenRouter",
                "base_url": "https://openrouter.ai/api/v1",
            }])
        if request.method == "POST" and request.url.path == "/api/tasks":
            body = json_body(request)
            return httpx.Response(201, json={"id": "task-1", **body})
        if request.method == "POST" and request.url.path == "/api/config-sets":
            body = json_body(request)
            return httpx.Response(201, json={"id": "config-set-1", **body})
        if request.method == "POST" and request.url.path == "/api/config-sets/config-set-1/slots":
            body = json_body(request)
            return httpx.Response(201, json={"id": f"slot-{len([c for c in calls if c[1].endswith('/slots')])}", **body})
        if request.method == "POST" and request.url.path == "/api/run-chains":
            body = json_body(request)
            return httpx.Response(201, json={"id": "chain-1", **body})
        if request.method == "POST" and request.url.path == "/api/runs":
            body = json_body(request)
            return httpx.Response(201, json={"id": "run-1", **body})
        if request.method == "POST" and request.url.path == "/api/runs/run-1/execute":
            return httpx.Response(200, json={"id": "run-1", "status": "complete"})
        if request.method == "GET" and request.url.path == "/api/runs/run-1/outputs":
            return httpx.Response(200, json=[
                {"provider_model_id": "m1", "status": "complete", "text": "one", "usage": {"output_tokens": 1}},
                {"provider_model_id": "m2", "status": "failed", "error": {"message": "nope"}},
            ])
        return httpx.Response(404, json={"detail": str(request.url)})

    original_client = httpx.Client
    httpx.Client = lambda *args, **kwargs: original_client(
        *args,
        transport=httpx.MockTransport(handler),
        **kwargs,
    )
    try:
        result = run_live_eval.main([
            "--provider-id", "provider-1",
            "--model", "m1",
            "--model", "m2",
            "--model", "m3",
            "--task-name", "Demo",
            "--chain-name", "Demo Chain",
            "--prompt", "Evaluate this.",
        ])
    finally:
        httpx.Client = original_client

    assert result == 0
    assert calls == [
        ("GET", "/api/health"),
        ("GET", "/api/config/providers"),
        ("POST", "/api/tasks"),
        ("POST", "/api/config-sets"),
        ("POST", "/api/config-sets/config-set-1/slots"),
        ("POST", "/api/config-sets/config-set-1/slots"),
        ("POST", "/api/config-sets/config-set-1/slots"),
        ("POST", "/api/run-chains"),
        ("POST", "/api/runs"),
        ("POST", "/api/runs/run-1/execute"),
        ("GET", "/api/runs/run-1/outputs"),
    ]
    output = capsys.readouterr().out
    assert "Review: http://localhost:8000/?chain=chain-1" in output
    assert "m2 failed" in output


def json_body(request: httpx.Request) -> dict:
    return __import__("json").loads(request.content.decode("utf-8"))
