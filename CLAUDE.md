# Tukey

## Dev Server
- The frontend is served directly by the backend at `http://localhost:8000` (NOT a separate Vite dev server)
- `uv run tukey` starts the full app (backend + UI)
- `npm run build` in `ui/` to rebuild the frontend; the backend serves the built assets

## Package Management
- Use `uv` for all Python dependency management (not pip, not poetry)
- `uv sync` to install, `uv run pytest` to run tests, etc.
- Primary languages: Python and TypeScript. Markdown and YAML for docs/config. Answer from existing knowledge — do not web search for library choices unless asked.

## LiteLLM
- Models routed through an OpenAI-compatible gateway need the `openai/` prefix (e.g. `openai/claude-4.6-sonnet`, `openai/gemini-2.5-pro`)
- Models not in LiteLLM's pricing DB must be registered via `litellm.register_model()` before use, or calls fail with "model isn't mapped yet"
- `register_model` takes a flat dict keyed by model name: `{model: {max_tokens, input_cost_per_token, ..., litellm_provider, mode}}`
- `litellm.completion_cost()` throws on unknown models — always wrap in try/except
- Gateway: `OPENAI_API_BASE` / `OPENAI_API_KEY` from `.env`

## Frontend Layout
- Every flex child that should shrink below content width needs `min-w-0` (flexbox defaults to `min-width: auto`)
- The overflow constraint chain must be unbroken from the root (`overflow-hidden`) through every flex container to the leaf content — one missing `min-w-0` or `overflow-hidden` lets content push the layout past the viewport
- ResizeObserver + setState can create infinite loops if the state change triggers a layout change that re-fires the observer; always round/threshold observed values before setting state
- ResponseCarousel uses fixed-width cards with horizontal scroll; card width is computed from container width and visible count

## Frontend Components
- Use shadcn components (`ui/src/components/ui/`) as the base for all new UI — don't build custom primitives
- Add new shadcn components via `npx shadcn@latest add <component>` in `ui/`
- Available: badge, button, dialog, input, label, popover, select, separator, slider, textarea, scroll-area, tooltip
