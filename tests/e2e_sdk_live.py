"""Live E2E test for the TukeyClient SDK.

Run against a live server: uv run python tests/e2e_sdk_live.py

Requires:
- Tukey server running at localhost:8000
- At least one provider configured with valid API keys
"""

from __future__ import annotations

import sys

from tukey.client import TukeyClient


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

    with TukeyClient(base_url=base_url) as client:
        # 1. Check providers exist
        providers = client.list_providers()
        if not providers:
            print("ERROR: No providers configured. Add one first.")
            sys.exit(1)
        print(f"Found {len(providers)} provider(s)")

        pid = providers[0]["id"]
        models_cfg = providers[0].get("models", [])
        if not models_cfg:
            # Use a default model config
            model_id = "openai/gpt-4o-mini"
            models = [{"provider_id": pid, "model_id": model_id, "display_name": model_id}]
        else:
            models = [{"provider_id": pid, "model_id": m, "display_name": m} for m in models_cfg[:1]]

        # 2. Create chatroom
        cr = client.create_chatroom("E2E SDK Test", models=models)
        print(f"Created chatroom: {cr['id']}")

        # 3. Run batch with 3 prompts
        prompts = [
            "Say hello in exactly 3 words.",
            "What is 2+2? Answer with just the number.",
            "Name one color. One word only.",
        ]
        chat, turns = client.run_batch(cr["id"], prompts)
        print(f"Chat {chat['id']}: sent {len(turns)} prompts")

        for i, turn in enumerate(turns):
            print(f"  Turn {i+1}: {len(turn.get('responses', []))} response(s)")
            for resp in turn.get("responses", []):
                err = resp.get("error", False)
                tok = resp.get("tokens_out", "?")
                cost = resp.get("cost")
                status = "ERROR" if err else "OK"
                print(f"    [{status}] tokens_out={tok} cost={cost}")

        # 4. Fetch manifest
        manifest = client.get_manifest(cr["id"], chat["id"])
        assert len(manifest["turns"]) == len(prompts), "Manifest turn count mismatch"
        print(f"Manifest: {len(manifest['turns'])} turns verified")

        # 5. Replay
        replay = client.replay_chat(cr["id"], chat["id"])
        replay_turns = replay["turns"]
        assert len(replay_turns) == len(prompts), "Replay turn count mismatch"
        print(f"Replay: {len(replay_turns)} turns replayed")

        # 6. Cleanup
        client.delete_chatroom(cr["id"])
        print("Chatroom deleted. E2E test passed!")


if __name__ == "__main__":
    main()
