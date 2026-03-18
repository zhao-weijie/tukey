# Tukey

## Package Management
- Use `uv` for all Python dependency management (not pip, not poetry)
- `uv sync` to install, `uv run pytest` to run tests, etc.

## LiteLLM
- Models routed through an OpenAI-compatible gateway need the `openai/` prefix (e.g. `openai/claude-4.6-sonnet`, `openai/gemini-2.5-pro`)
- Models not in LiteLLM's pricing DB must be registered via `litellm.register_model()` before use, or calls fail with "model isn't mapped yet"
- `register_model` takes a flat dict keyed by model name: `{model: {max_tokens, input_cost_per_token, ..., litellm_provider, mode}}`
- `litellm.completion_cost()` throws on unknown models — always wrap in try/except
- Gateway: `OPENAI_API_BASE` / `OPENAI_API_KEY` from `.env`
