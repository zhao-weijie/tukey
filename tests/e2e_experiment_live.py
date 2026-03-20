#!/usr/bin/env python3
"""Live E2E test for the experiment framework.

Requires a running Tukey server with at least one provider configured.
Usage: uv run python tests/e2e_experiment_live.py
"""

from tukey.client import TukeyClient


def main():
    c = TukeyClient()

    # Setup: create provider + chatroom
    providers = c.list_providers()
    if not providers:
        print("No providers configured. Add one first.")
        return
    pid = providers[0]["id"]

    cr = c.create_chatroom("E2E Experiment Room", models=[
        {"provider_id": pid, "model_id": providers[0].get("provider", "openai") + "/gpt-4o-mini", "display_name": "GPT-4o-mini"},
    ])
    print(f"Chatroom: {cr['id']}")

    # Create experiment
    exp = c.create_experiment("E2E Test", cr["id"], {
        "decision": "Evaluate response quality",
        "criteria": [{"id": "c1", "name": "accuracy", "type": "binary", "description": "Correct?"}],
        "judges": ["human"],
    })
    print(f"Experiment: {exp['id']}")

    # Add test cases
    cases = c.add_test_cases(exp["id"], [
        {"turns": [{"role": "user", "content": "What is 2+2?"}]},
        {"turns": [
            {"role": "user", "content": "Hello"},
            {"role": "user", "content": "What did I just say?"},
        ]},
    ])
    print(f"Test cases: {len(cases)}")

    # Run
    run = c.run_experiment(exp["id"])
    print(f"Run: {run['id']} status={run['status']}")

    # Results
    results = c.get_results(exp["id"], run["id"])
    print(f"Results: {len(results)}")
    for r in results:
        print(f"  model={r['model_id']} exchanges={len(r['exchanges'])} cost={r['total_cost']:.4f} error={r['error']}")

    # Annotate first result
    if results:
        ann = c.add_annotation(exp["id"], run["id"],
            result_id=results[0]["id"], verdict="pass", judge="human", notes="Looks good")
        print(f"Annotation: {ann['id']}")

    # Summary
    summary = c.get_run_summary(exp["id"], run["id"])
    print(f"Summary: {summary}")

    # Cleanup
    c.delete_experiment(exp["id"])
    c.delete_chatroom(cr["id"])
    print("Done — cleaned up.")


if __name__ == "__main__":
    main()
