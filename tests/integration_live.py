"""Integration test: fan-out a prompt to 3 models via the live gateway."""

import asyncio
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from tukey.storage import Storage
from tukey.config import ConfigManager
from tukey.chat.room import ChatRoom


async def main():
    api_key = os.environ["OPENAI_API_KEY"]
    api_base = os.environ["OPENAI_API_BASE"]

    tmp_dir = Path("/tmp/tukey_integration_test")
    storage = Storage(tmp_dir)
    storage.ensure_dirs()
    config = ConfigManager(storage)

    # Register the gateway as a single provider
    prov = config.add_provider(
        provider="openai",
        api_key=api_key,
        base_url=api_base,
        display_name="Gateway",
    )
    pid = prov["id"]

    models = [
        {"provider_id": pid, "model_id": "openai/claude-4.6-sonnet", "display_name": "Claude 4.6 Sonnet"},
        {"provider_id": pid, "model_id": "openai/gpt-5.2", "display_name": "GPT 5.2"},
        {"provider_id": pid, "model_id": "openai/gemini-2.5-pro", "display_name": "Gemini 2.5 Pro"},
    ]

    room = ChatRoom(storage, config)
    room.create("Integration Test", models=models)

    prompt = "What is 2+2? Reply with just the number."
    print(f"Sending prompt to {len(models)} models: {prompt!r}\n")

    start = time.perf_counter()
    turn = await room.send_message(prompt)
    total_ms = (time.perf_counter() - start) * 1000

    ok = True
    for resp in turn["responses"]:
        mid = resp["model_id"]
        meta = room.get_meta()
        name = next((m["display_name"] for m in meta["models"] if m["id"] == mid), mid)
        err = resp.get("error")
        if err:
            print(f"  FAIL  {name}: {resp['content']}")
            ok = False
        else:
            print(f"  OK    {name}")
            print(f"        content:  {resp['content'][:120]}")
            print(f"        tokens:   {resp['tokens_in']} in / {resp['tokens_out']} out")
            print(f"        cost:     ${resp['cost']:.6f}")
            print(f"        latency:  {resp['duration_ms']:.0f}ms")
            print(f"        speed:    {resp['tokens_per_sec']:.1f} tok/s")
            print()

    print(f"Total wall time: {total_ms:.0f}ms (parallel fan-out)")

    # Verify persistence
    msgs = storage.read_messages(room.room_id)
    assert len(msgs) == 1, f"Expected 1 message, got {len(msgs)}"
    assert len(msgs[0]["responses"]) == len(models)
    print("Persistence check: OK")

    # Cleanup
    import shutil
    shutil.rmtree(tmp_dir)

    if not ok:
        sys.exit(1)
    print("\nAll models responded successfully.")


if __name__ == "__main__":
    asyncio.run(main())
