# Tukey

## Dev Server
- The frontend is served directly by the backend at `http://localhost:8000` (NOT a separate Vite dev server)
- `uv run tukey` starts the full app (backend + UI)
- `npm run build` in `ui/` to rebuild the frontend; the backend serves the built assets

## Package Management
- Use `uv` for all Python dependency management (not pip, not poetry)
- `uv sync` to install, `uv run pytest` to run tests, etc.
- No python or python3 installed. use `uv run` for ANY scripts.
- Primary languages: Python and TypeScript. Markdown and YAML for docs/config. Answer from existing knowledge — do not web search for library choices unless asked.

## LLM Provider
- All LLM calls go through `OpenAICompatibleProvider` in `tukey/providers/openai_provider.py` — direct httpx to the OpenAI Chat Completions API format
- Works with OpenRouter, OpenAI, and any OpenAI-compatible gateway (Anthropic, Google, etc. via OpenRouter)
- Model pricing + capabilities fetched from LiteLLM's public JSON and cached to `~/.tukey/model_prices.json` (24h TTL)
- The `openai/` prefix in stored model IDs is stripped before sending to the API (legacy from LiteLLM routing)
- Cost is `None` for models not in the pricing database — this is safe, the UI handles it gracefully

## Frontend Layout
- Every flex child that should shrink below content width needs `min-w-0` (flexbox defaults to `min-width: auto`)
- The overflow constraint chain must be unbroken from the root (`overflow-hidden`) through every flex container to the leaf content — one missing `min-w-0` or `overflow-hidden` lets content push the layout past the viewport
- ResizeObserver + setState can create infinite loops if the state change triggers a layout change that re-fires the observer; always round/threshold observed values before setting state
- ResponseCarousel uses fixed-width cards with horizontal scroll; card width is computed from container width and visible count

## Frontend Components
- Use shadcn components (`ui/src/components/ui/`) as the base for all new UI — don't build custom primitives
- Add new shadcn components via `npx shadcn@latest add <component>` in `ui/`
- Available: badge, button, dialog, input, label, popover, select, separator, slider, textarea, scroll-area, tooltip

---
## Last codebase exploration output

1. WHAT THIS PROJECT DOES

Tukey is an LLM comparison workbench — a local-first web application that lets teams systematically compare
language models side-by-side rather than relying on intuition. It's designed for both casual exploration and
rigorous experimentation.

Core tagline: "Compare LLM responses side-by-side with local persistence"

Key value proposition:
- Parallel streaming responses from any mix of OpenAI, Anthropic, Google, DeepSeek, or OpenAI-compatible
providers
- Local data storage (~/.tukey/) — nothing leaves your machine except API calls
- Scientific evaluation framework (experiments, test cases, human annotations)
- Built-in synthesis tools to analyze patterns across responses
- REST API + Python SDK for programmatic use

---
2. CURRENT USER ONBOARDING FLOW

A new user follows this path:

1. Installation (pipx or uv)
pipx install tukey-llm
# or
uv tool install tukey-llm
2. Start server
tukey
# Opens http://localhost:8000
3. Configure providers (Settings tab in sidebar)
    - Add API key + provider type (openai/anthropic/google/custom)
    - Tukey stores in ~/.tukey/config.json
    - Can test connectivity before use
4. Create a chatroom (sidebar: "+ New Chatroom")
    - Name it
    - Add models from dropdown (drawn from configured providers)
    - Per-model config: system prompt, temperature, max_tokens, top_p, etc.
5. Start comparing
    - Type a prompt
    - Send — all models respond in parallel with streaming
    - Toggle metadata bar to see tokens, cost, duration
    - Cycle through multiple completions per model
    - Annotate interesting text ranges (thumbs up/down + comment)
6. Optional: Run experiments
    - Define test cases (multi-turn prompts)
    - Batch execute across models
    - Domain experts annotate results
    - Export manifest for reproducibility

---
3. FEATURES CURRENTLY IMPLEMENTED

Chat/Comparison Features (Complete):
- Side-by-side streaming responses (all models in parallel)
- Multiple completions per model (n=1–9) for variance observation
- Response cycling (< 1/3 > per model independently)
- Per-response metadata: tokens in/out, cost, duration, tok/s
- Full-text search across all chats
- Multi-turn with branching (conversation history follows selected response)
- Markdown rendering of responses
- Copy individual responses or code blocks
- Chat import/export (per-chatroom JSON)

Model Configuration (Complete):
- Independent per-model config: system prompt, temperature, max_tokens, top_p, response_format, tools
- "Apply to all" broadcast for batch config changes
- Model capabilities detection (reasoning support, max tokens, etc.)

Persistence & Data Sovereignty (Complete):
- All data in ~/.tukey/ (default) or custom --data-dir
- No cloud sync, full local ownership
- Reproducible manifests (inputs + outputs for replay)
- Chat replay (re-run exact same prompts)

Annotation (Complete - US5.2):
- Select text in any response → rate (👍/👎) + comment
- Highlights persist (green=positive, red=negative)
- Click highlights to review/edit/delete annotations
- Survives page refresh, stored per response

Provider Integration:
- Unified interface via LiteLLM (supports 100+ models)
- Dynamic provider registration (handles unknown models gracefully)
- Custom OpenAI-compatible gateways (base_url override)
- Provider test endpoint (validate API keys before use)

Experiments (Partial - US5.1, 5.3, 5.4):
- Backend fully implemented:
    - Create named, versioned experiments
    - Define test cases (multi-turn prompts, tags, overrides)
    - Run execution with concurrency + progress tracking
    - Batch result annotations
    - Export reproducible manifests
- Frontend NOT yet built — use REST API or SDK only

Synthesis/Analysis (Partial - US6):
- Data contract ExperimentBundle + tool protocol SynthesisTool complete
- Built-in tools working:
    - basic_stats — per-model token/word/cost/latency counts
    - tfidf — vocabulary-level similarity analysis
- CLI interface: python -m tukey.synthesis.cli <id> [--tools tool1,tool2]
- Frontend UI not yet built — use CLI only

Programmatic Interface (Complete - US4):
- REST API with FastAPI/OpenAPI docs at /docs
- Python SDK client (TukeyClient) via httpx
- Full CRUD for chatrooms, chats, messages, annotations
- WebSocket streaming support

UX/Accessibility:
- Responsive sidebar (drawer overlay on mobile <768px)
- Loading skeletons during streaming
- Delete confirmations
- Metadata toggle via ChartBar icon
- Theme-aware (light/dark mode)

---
4. SETUP & INSTALLATION PROCESS

Dependencies:

Python:
- FastAPI, uvicorn (web server)
- litellm ≥1.40.0 (unified LLM interface)
- Pydantic 2.0+ (validation)
- httpx (async HTTP client)
- websockets (streaming)
- python-dotenv (config)

Frontend (TypeScript):
- React 19, Vite build tool
- Tailwind CSS 4 + Tailwind CSS Vite plugin
- shadcn components (base UI library)
- Zustand (state management)
- React Markdown + highlight.js (rendering)
- Phosphor Icons, Lucide (icon sets)

Installation steps (contributing):

git clone https://github.com/zhao-weijie/tukey.git
cd tukey

# Python
uv sync --extra dev          # install + dev dependencies

# Frontend
cd ui
npm ci                       # install deps
npm run build                # compile TypeScript + build for production
cd ..

# Run
uv run tukey                 # starts at http://localhost:8000

Configuration:
- Minimal: just add API keys via Settings UI
- Advanced: .env file for gateway routing, retry settings (optional)
- Storage: --data-dir flag or ~/.tukey default

---
5. WHAT A NEW USER NEEDS TO GET VALUE

Minimum viable path (5 minutes):

1. Install: pipx install tukey-llm
2. Run: tukey
3. Go to http://localhost:8000/api/health to verify
4. Click "Providers" → add OpenAI API key
5. Create chatroom, add Claude + GPT
6. Type a prompt, hit send
7. Compare responses

Full featured (30 minutes):

8. Adjust per-model settings (temperature, system prompt)
9. Generate 3 completions per model
10. Annotate interesting text sections
11. Export chatroom as JSON
12. Read cost/latency in metadata bar

Experimental evaluation (1–2 hours):

13. Create experiment with test cases
14. Run batch execution
15. Share results with domain experts
16. Experts annotate (pass/fail + notes)
17. Export manifest for reproducibility
18. Run synthesis tools (basic_stats, tfidf)

---
KEY ARCHITECTURAL INSIGHTS

Backend Structure (Python):
tukey/
├── server/               # FastAPI app + routes
│   ├── app.py           # app factory
│   ├── websocket.py     # streaming endpoint
│   └── routes/
│       ├── chat.py      # chatroom/chat CRUD
│       ├── config.py    # provider CRUD
│       ├── models.py    # model listing + capabilities
│       ├── experiments.py # experiment CRUD + execution
│       └── search.py    # full-text search
├── chat/room.py         # ChatRoom class (fanout, streaming)
├── experiment/engine.py # Experiment class (test execution)
├── config/manager.py    # ConfigManager (provider persistence)
├── storage/store.py     # Storage (JSONL/JSON file I/O)
├── providers/
│   ├── litellm_provider.py  # unified LLM interface via LiteLLM
│   └── base.py          # StreamChunk + LLMResponse types
└── synthesis/           # Analysis tools + data contracts

Frontend Structure (React + TypeScript):
ui/src/
├── components/
│   ├── ChatRoom.tsx     # main chat UI, message send, carousel
│   ├── ResponseCard.tsx # individual response card w/ annotation
│   ├── Sidebar.tsx      # chatroom/chat list, provider setup
│   ├── ProviderSetup.tsx # API key + provider dialog
│   ├── ModelConfig.tsx   # per-model param editing
│   ├── SearchDialog.tsx  # full-text search
│   └── ui/              # shadcn components (button, input, dialog, etc.)
├── stores/
│   ├── chatStore.ts     # Zustand: chatrooms, chats, messages, streaming state
│   └── annotationStore.ts # annotations per chat
├── hooks/
│   └── useChat.ts       # WebSocket connection + streaming
└── lib/api.ts           # HTTP client for REST endpoints

Data Flow:
1. User types prompt → send via WebSocket /ws/chat/{chatroom_id}/{chat_id}
2. ChatRoom.send_message() → LiteLLMProvider.complete() (fan-out)
3. Streaming chunks → WebSocket → ResponseCard (renders as content arrives)
4. Stored in ~/.tukey/chatrooms/{id}/chats/{id}/messages.jsonl
5. Annotations stored separately, tied to (message_id, model_id, response_index)

Streaming Architecture:
- WebSocket connection per chat session
- Server uses asyncio to fan-out to multiple models concurrently
- Each response chunk includes metadata (tokens, cost, duration on completion)
- Client collects chunks, re-renders card incrementally

---
KEY FILES TO UNDERSTAND THE PROJECT

Python Entry Points:
- /C:/Users/zhaow/Documents/Github/tukey/tukey/tukey/__main__.py — CLI entry point
- /C:/Users/zhaow/Documents/Github/tukey/tukey/tukey/server/app.py — FastAPI app factory
- /C:/Users/zhaow/Documents/Github/tukey/tukey/tukey/chat/room.py — ChatRoom (core logic)
- /C:/Users/zhaow/Documents/Github/tukey/tukey/tukey/experiment/engine.py — Experiment CRUD + execution

Frontend Entry Points:
- /C:/Users/zhaow/Documents/Github/tukey/tukey/ui/src/App.tsx — top-level layout
- /C:/Users/zhaow/Documents/Github/tukey/tukey/ui/src/components/ChatRoom.tsx — main UI
- /C:/Users/zhaow/Documents/Github/tukey/tukey/ui/src/stores/chatStore.ts — state management

Configuration & Storage:
- /C:/Users/zhaow/Documents/Github/tukey/tukey/pyproject.toml — Python dependencies
- /C:/Users/zhaow/Documents/Github/tukey/tukey/README.md — user-facing docs
- /C:/Users/zhaow/Documents/Github/tukey/tukey/requirements.md — feature roadmap & US definitions
- /C:/Users/zhaow/Documents/Github/tukey/tukey/.env — optional gateway/retry config

Routes (REST API):
- GET /api/health — server status + data directory
- POST /api/chat/chatrooms — create chatroom
- POST /api/chat/chatrooms/{id}/chats/{id}/messages — send prompt (uses WebSocket for streaming)
- GET /api/config/providers — list API providers
- POST /api/config/providers — add provider (API key)
- GET /api/models/{id}/capabilities — check model features
- /ws/chat/{chatroom_id}/{chat_id} — WebSocket for streaming
- POST /api/experiments — create experiment
- Full docs: http://localhost:8000/docs

---
Summary: Tukey is a production-ready LLM comparison tool with a modern React frontend and Python/FastAPI
backend. It emphasizes local-first data ownership, reproducibility, and team collaboration through
structured experiments and human annotation. The core chat experience is fully functional; experiments and
synthesis tools have complete backends but lack UI polish.