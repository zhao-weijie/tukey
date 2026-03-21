#!/usr/bin/env python3
"""Live E2E test for the experiment framework.

Requires a running Tukey server with at least one provider configured.
Usage: uv run python tests/e2e_experiment_live.py [http://localhost:8000]
"""

import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"


def get(client: httpx.Client, path: str) -> dict:
    r = client.get(f"{BASE}{path}")
    r.raise_for_status()
    return r.json()


def post(client: httpx.Client, path: str, body: dict) -> dict:
    r = client.post(f"{BASE}{path}", json=body)
    r.raise_for_status()
    return r.json()


def delete(client: httpx.Client, path: str) -> None:
    r = client.delete(f"{BASE}{path}")
    r.raise_for_status()


def main():
    with httpx.Client(timeout=120) as client:
        providers = get(client, "/api/config/providers")
        if not providers:
            print("No providers configured. Add one first.")
            return
        pid = providers[0]["id"]

        cr = post(client, "/api/chat/chatrooms", {
            "name": "E2E Experiment Room",
            "models": [{"provider_id": pid, "model_id": providers[0].get("provider", "openai") + "/gpt-4o-mini", "display_name": "GPT-4o-mini"}],
        })
        print(f"Chatroom: {cr['id']}")

        exp = post(client, "/api/experiments", {
            "name": "E2E Test",
            "chatroom_id": cr["id"],
            "brief": {
                "decision": "Evaluate response quality",
                "criteria": [{"id": "c1", "name": "accuracy", "type": "binary", "description": "Correct?"}],
                "judges": ["human"],
            },
        })
        print(f"Experiment: {exp['id']}")

        cases = post(client, f"/api/experiments/{exp['id']}/test-cases", {
            "test_cases": [
                {"turns": [{"role": "user", "content": "What is 2+2?"}]},
                {"turns": [
                    {"role": "user", "content": "Hello"},
                    {"role": "user", "content": "What did I just say?"},
                ]},
            ],
        })
        print(f"Test cases: {len(cases)}")

        run = post(client, f"/api/experiments/{exp['id']}/run", {})
        print(f"Run: {run['id']} status={run['status']}")

        results = get(client, f"/api/experiments/{exp['id']}/runs/{run['id']}/results")
        print(f"Results: {len(results)}")
        for r in results:
            print(f"  model={r['model_id']} exchanges={len(r['exchanges'])} cost={r['total_cost']:.4f} error={r['error']}")

        if results:
            ann = post(client, f"/api/experiments/{exp['id']}/runs/{run['id']}/annotations", {
                "result_id": results[0]["id"], "verdict": "pass", "judge": "human", "notes": "Looks good",
            })
            print(f"Annotation: {ann['id']}")

        summary = get(client, f"/api/experiments/{exp['id']}/runs/{run['id']}/summary")
        print(f"Summary: {summary}")

        delete(client, f"/api/experiments/{exp['id']}")
        delete(client, f"/api/chat/chatrooms/{cr['id']}")
        print("Done -- cleaned up.")


if __name__ == "__main__":
    main()
