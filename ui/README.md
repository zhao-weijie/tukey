# Tukey UI

React frontend for Tukey — a side-by-side LLM comparison tool. The UI lets users configure models, send prompts to multiple LLMs simultaneously, and compare streaming responses in a carousel layout.

## Tech stack

- **React 19** + **TypeScript** (strict mode, ES2023 target)
- **Vite 7** — bundler and dev server
- **Tailwind CSS 4** — styling via `@tailwindcss/vite` plugin
- **Zustand** — single global store (`chatStore.ts`)
- **shadcn/ui** — base UI primitives (Button, Badge, Dialog, ScrollArea, etc.)
- **Phosphor Icons** — icon library
- **react-markdown** + **remark-gfm** + **rehype-highlight** — markdown rendering with syntax highlighting in LLM responses

## Project structure

```
ui/
├── src/
│   ├── App.tsx                  # Root layout: Sidebar + ChatRoom
│   ├── main.tsx                 # Entry point
│   ├── index.css                # Tailwind imports, theme variables, markdown prose styles
│   ├── components/
│   │   ├── Sidebar.tsx          # Chatroom/chat list, create/delete
│   │   ├── ChatRoom.tsx         # Main chat view: message history, input, streaming
│   │   ├── ResponseCard.tsx     # Single model response card (markdown, copy, metadata)
│   │   ├── ResponseCarousel.tsx # Horizontal scroll container for response cards
│   │   ├── MarkdownContent.tsx  # Markdown renderer with code block copy buttons
│   │   ├── CopyButton.tsx       # Reusable copy-to-clipboard button
│   │   ├── ModelConfig.tsx      # Model configuration panel (provider, params)
│   │   ├── ProviderSetup.tsx    # Provider (API) connection setup
│   │   ├── SearchDialog.tsx     # Search/filter dialog
│   │   └── ui/                  # shadcn primitives (badge, button, card, dialog, etc.)
│   ├── stores/
│   │   └── chatStore.ts         # Zustand store: chatrooms, chats, messages, streaming state
│   ├── hooks/
│   │   └── useChat.ts           # WebSocket hook for real-time streaming
│   └── lib/
│       ├── api.ts               # REST API client (fetch wrapper)
│       └── utils.ts             # cn() and other utilities
├── vite.config.ts               # Vite config with proxy to backend and path aliases
├── tsconfig.app.json            # TypeScript config
└── package.json
```

## Development

The frontend is served by the backend in production. For development:

```bash
# Install dependencies
npm install

# Build (required before running the backend)
npm run build

# Start the full app (backend serves built UI)
cd .. && uv run tukey
```

The Vite config includes a dev proxy (`/api` → `:8000`, `/ws` → `ws://:8000`) for use with `npm run dev` if needed, but the standard workflow is `npm run build` then `uv run tukey`.

## Architecture notes

- **Single-page app** — `App.tsx` renders a `Sidebar` (chatroom/chat navigation) and `ChatRoom` (main content area) side by side.
- **Streaming** — `useChat.ts` manages a WebSocket connection per chat. Streaming tokens update the Zustand store, and `ResponseCard` renders them incrementally via `MarkdownContent`.
- **Response carousel** — Each user turn shows one `ResponseCard` per model in a horizontally scrollable `ResponseCarousel`. When multiple completions exist per model, cards include prev/next cycling controls.
- **Markdown rendering** — LLM responses are rendered as markdown with GFM support (tables, strikethrough, task lists) and syntax-highlighted code blocks. Code blocks have a hover copy button; each response card has a copy-full-response button in the header.
- **Theming** — Light/dark mode via CSS variables on `:root` / `.dark` class. All custom styles (markdown prose, highlight.js) use theme-aware CSS variables.
- **Path alias** — `@/` maps to `src/` via both Vite (`resolve.alias`) and TypeScript (`paths`).
