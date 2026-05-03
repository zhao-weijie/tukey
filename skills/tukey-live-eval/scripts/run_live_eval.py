#!/usr/bin/env python
"""Create and execute a three-model text eval through Tukey's REST API."""

from __future__ import annotations

import argparse
import json
import sys

import httpx


SETUP_GUIDANCE = (
    "No OpenRouter-compatible provider found. Start Tukey with `uv run tukey`, "
    "open http://localhost:8000, and add OpenRouter in the UI. This script "
    "does not collect provider secrets."
)


def api(client: httpx.Client, method: str, path: str, **kwargs):
    response = client.request(method, path, **kwargs)
    response.raise_for_status()
    return response.json()


def is_openrouter(provider: dict) -> bool:
    text = " ".join(str(provider.get(key) or "") for key in ("provider", "display_name", "base_url"))
    return "openrouter" in text.lower()


def pick_provider(providers: list[dict], provider_id: str | None) -> dict:
    if provider_id:
        matches = [provider for provider in providers if provider.get("id") == provider_id]
        if not matches:
            raise SystemExit(f"Provider not found: {provider_id}")
        if not is_openrouter(matches[0]):
            raise SystemExit(f"Provider is not OpenRouter-compatible: {provider_id}")
        return matches[0]

    for provider in providers:
        if is_openrouter(provider):
            return provider
    raise SystemExit(SETUP_GUIDANCE)


def require_three(models: list[str]) -> list[str]:
    unique = list(dict.fromkeys(models))
    if len(unique) != 3:
        raise SystemExit("Pass exactly three distinct --model values.")
    return unique


def create_records(client: httpx.Client, args, provider: dict, models: list[str]) -> dict:
    task = api(client, "POST", "/api/tasks", json={
        "name": args.task_name,
        "description": "Codex-driven live evaluation task",
        "tags": ["codex-live-eval"],
    })
    config_set = api(client, "POST", "/api/config-sets", json={
        "name": f"{args.task_name} - Codex live eval",
        "description": "Created by the Tukey live eval Codex skill",
        "tags": ["codex-live-eval"],
    })
    for index, model in enumerate(models, start=1):
        api(client, "POST", f"/api/config-sets/{config_set['id']}/slots", json={
            "name": f"Model {index}",
            "provider_id": provider["id"],
            "provider_model_id": model,
            "display_name": model,
            "system_prompt": args.system_prompt or "",
            "temperature": args.temperature,
            "task_type": "chat_completion",
            "modality": "text",
        })

    chain = api(client, "POST", "/api/run-chains", json={
        "name": args.chain_name,
        "default_config_set_id": config_set["id"],
    })
    run = api(client, "POST", "/api/runs", json={
        "name": f"{args.task_name} live eval",
        "kind": "agent",
        "status": "queued",
        "config_set_id": config_set["id"],
        "task_id": task["id"],
        "chain_id": chain["id"],
        "created_by": "agent",
    })
    run = api(client, "POST", f"/api/runs/{run['id']}/execute", json={
        "n": args.n,
        "created_by": "agent",
        "inputs": [{
            "role": "user",
            "content": [{"type": "text", "text": args.prompt}],
            "source": {"type": "agent", "ref_id": "codex-live-eval"},
        }],
    })
    outputs = api(client, "GET", f"/api/runs/{run['id']}/outputs")
    return {"task": task, "config_set": config_set, "chain": chain, "run": run, "outputs": outputs}


def preview(text: str | None, limit: int = 240) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def print_summary(base_url: str, records: dict) -> None:
    chain = records["chain"]
    run = records["run"]
    print(f"Task: {records['task']['name']} ({records['task']['id']})")
    print(f"Config set: {records['config_set']['id']}")
    print(f"Chain: {chain['name']} ({chain['id']})")
    print(f"Run: {run.get('status')} ({run['id']})")
    print(f"Review: {base_url}/?chain={chain['id']}")
    print("Outputs:")
    for output in records["outputs"]:
        usage = output.get("usage") or {}
        usage_text = ", ".join(f"{key}={usage[key]}" for key in sorted(usage) if usage[key] is not None)
        suffix = f" [{usage_text}]" if usage_text else ""
        print(f"- {output.get('provider_model_id')} {output.get('status')}{suffix}: {preview(output.get('text'))}")
        if output.get("error"):
            print(f"  error: {json.dumps(output['error'], sort_keys=True)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--provider-id")
    parser.add_argument("--model", action="append", default=[])
    parser.add_argument("--task-name", required=True)
    parser.add_argument("--chain-name", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--system-prompt")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--n", type=int, default=1)
    args = parser.parse_args(argv)

    base_url = args.base_url.rstrip("/")
    models = require_three(args.model)
    try:
        with httpx.Client(base_url=base_url, timeout=300.0) as client:
            api(client, "GET", "/api/health")
            provider = pick_provider(api(client, "GET", "/api/config/providers"), args.provider_id)
            records = create_records(client, args, provider, models)
        print_summary(base_url, records)
        return 0
    except httpx.HTTPError as exc:
        print(f"Tukey API request failed: {exc}", file=sys.stderr)
        return 1
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
