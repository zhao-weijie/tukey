---
name: tukey-live-eval
description: Run a Codex-driven Tukey live evaluation over text models. Use when Codex should discover Tukey's local API, select three OpenRouter text models, interview the user for one test case, run the bundled REST helper, and leave a reviewable run chain in the Tukey frontend.
---

# Tukey Live Eval

Use this skill as a starting point for a short, text-only Tukey evaluation. Discover details from the running API instead of carrying a local copy of the product model. Use only public REST endpoints; never read or write Tukey storage files directly, and never ask for provider secrets.

## Workflow

1. Confirm Tukey is running at `http://localhost:8000` with `GET /api/health`. If not, tell the user to start it with `uv run tukey`.

2. Discover the current API from `http://localhost:8000/docs` when needed. The expected starting endpoints are:
   - `GET /api/config/providers`
   - `GET /api/models/providers/{provider_id}/available`
   - `POST /api/tasks`, `/api/config-sets`, `/api/run-chains`, `/api/runs`
   - `POST /api/runs/{run_id}/execute`

3. Pick an OpenRouter-compatible provider from `GET /api/config/providers`. If none exists, stop and direct the user to configure OpenRouter in the Tukey UI; do not handle API keys in chat.

4. Query `GET /api/models/providers/{provider_id}/available`, choose exactly three likely text chat model IDs, and explain the shortlist briefly. Avoid obvious image, embedding, audio, moderation, rerank, TTS, STT, or vision-only models.

5. Interview the user for one task name and one concrete prompt/test input. Ask for a system prompt only when it matters.

6. Run the bundled helper:

```powershell
uv run python .\skills\tukey-live-eval\scripts\run_live_eval.py `
  --base-url http://localhost:8000 `
  --provider-id <provider_id> `
  --model <model_id_1> `
  --model <model_id_2> `
  --model <model_id_3> `
  --task-name "<task name>" `
  --chain-name "<chain name>" `
  --prompt "<user test prompt>" `
  --system-prompt "<optional system prompt>"
```

7. Report the printed task/config/chain/run IDs, per-model output status, and review URL. Direct the user to the run chain in the frontend for annotation.
