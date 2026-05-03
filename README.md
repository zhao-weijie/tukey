# Tukey

Tukey is a local-first workbench for comparing model configurations with reproducible runs instead of one-off vibes checks.

The current product model is **tasks**, **config sets**, **immutable config versions**, **runs**, and **run chains**. Legacy chatroom and experiment routes may still exist for compatibility, but they are not the active UI or target API surface.

![Tukey side-by-side LLM comparison](docs/screenshot.png)

## Quick Install

```bash
uv tool install tukey-llm
tukey
```

Tukey serves the backend and frontend together at [http://localhost:8000](http://localhost:8000). On first launch, the guided setup helps you connect a provider, create a config set, create a task, and start a run chain.

For local development:

```bash
uv sync --extra dev
cd ui
npm ci
npm run build
cd ..
uv run tukey
```

### Options

```bash
tukey --port 9000           # different port (default: 8000)
tukey --host 127.0.0.1      # bind to localhost only
tukey --data-dir ./my-data  # custom data directory (default: ~/.tukey)
```

## Core Concepts

- **Task**: the use case you are evaluating, such as "support email triage" or "invoice field extraction".
- **Config set**: a reusable collection of model/config slots. Each slot records provider route, model ID, display name, system prompt, sampling parameters, tools, response format, and task type.
- **Config version**: an immutable snapshot of a slot once it is used by a run.
- **Run**: one prompt or test case executed against a config set. Runs store exact config versions, inputs, outputs, metadata, costs, latency, errors, annotations, and artifacts.
- **Run chain**: a chat-like sequence of linked runs with explicit lineage.
- **Eval plan**: optional orchestration for formal evals. It groups criteria, test cases, config sets, and schedules, but runs remain the execution primitive.

## What It Does

- **Parallel comparison**: run one prompt across every active slot in a config set.
- **Multiple completions**: generate 1-9 completions per slot to inspect response variance.
- **Run chains**: keep exploratory work in a conversation-like view while preserving run lineage.
- **Per-output metadata**: inspect cost, duration, token counts, and provider/model details.
- **Local-first storage**: data lives in your configured Tukey data directory, defaulting to `~/.tukey/`.
- **Run-native search**: search tasks, run chains, run inputs, outputs, and annotation comments.
- **Run-chain export**: export a run chain with runs, inputs, outputs, annotations, artifacts, config sets, slots, and config versions.
- **Annotations**: add review notes to completed run outputs.
- **Multimodal substrate**: backend run execution supports text, image generation, and image editing task types with local artifact storage. Frontend image review is still being built.

## Configuration

The fastest setup path is OpenRouter: one API key gives access to many providers and models. You can also add OpenAI-compatible endpoints directly.

Supported provider setup fields:

| Provider | What to enter |
| --- | --- |
| OpenRouter | API key from openrouter.ai/keys and `https://openrouter.ai/api/v1` |
| OpenAI-compatible | Base URL plus API key for OpenAI, local servers, or custom gateways |

Keys are stored locally in `~/.tukey/config.json` by default. You can switch data directories from the folder path in the sidebar.

## Codex Live Eval

Tukey includes a repo-local Codex skill for a short text-only live evaluation: `skills/tukey-live-eval/SKILL.md`. It guides Codex to discover configured OpenRouter models, interview you for one test case, run exactly three models through the run-native REST API, summarize outputs, and leave a run chain you can annotate in the frontend.

The executable helper is:

```bash
uv run python skills/tukey-live-eval/scripts/run_live_eval.py --base-url http://localhost:8000 --provider-id <provider-id> --model <model-a> --model <model-b> --model <model-c> --task-name "Support triage" --chain-name "Support triage live eval" --prompt "Classify this support email..."
```

It never reads or writes Tukey storage directly and does not collect provider secrets. Configure OpenRouter in the UI first if no suitable provider exists.

## REST API Example

The active API creates a queued run, then executes it explicitly:

```python
import httpx

BASE = "http://localhost:8000"

with httpx.Client(timeout=120) as client:
    config_sets = client.get(f"{BASE}/api/config-sets").json()
    config_set_id = config_sets[0]["id"]

    chains = client.get(f"{BASE}/api/run-chains").json()
    chain_id = chains[0]["id"]

    run = client.post(
        f"{BASE}/api/runs",
        json={
            "name": "API smoke run",
            "kind": "interactive",
            "status": "queued",
            "config_set_id": config_set_id,
            "chain_id": chain_id,
        },
    ).json()

    executed = client.post(
        f"{BASE}/api/runs/{run['id']}/execute",
        json={
            "n": 1,
            "created_by": "api",
            "inputs": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Reply with a one sentence hello."}
                    ],
                }
            ],
        },
    ).json()

    outputs = client.get(f"{BASE}/api/runs/{run['id']}/outputs").json()
    for output in outputs:
        print(output["provider_model_id"], output.get("text") or output["content"])
```

Useful endpoints:

- `GET /api/health`
- `GET /api/tasks`
- `GET /api/config-sets`
- `GET /api/config-sets/{config_set_id}/slots`
- `POST /api/runs`
- `POST /api/runs/{run_id}/execute`
- `GET /api/runs/{run_id}/outputs`
- `GET /api/run-chains/{chain_id}/detail`
- `POST /api/run-chains/{chain_id}/export`
- `GET /api/search?q=...`

Full endpoint reference is available while the server is running at [http://localhost:8000/docs](http://localhost:8000/docs).

## Current Gaps

- Frontend image artifact rendering and image-edit input controls are still in progress.
- Selected-output continuation for branched run chains is not fully surfaced end to end.
- Formal eval plans and synthesis still need to move fully onto run-native bundles.
- Legacy chatroom and experiment routes remain temporarily for compatibility and tests.

## Contributing

```bash
git clone https://github.com/zhao-weijie/tukey.git
cd tukey
uv sync --extra dev
cd ui && npm ci && npm run build && cd ..
uv run tukey
```

Run tests with:

```bash
uv run pytest
```

## License

MIT
