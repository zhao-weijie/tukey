# Tukey MVP — Implementation Status

## User Journey: Fresh Install → Daily Use

### 1. Install & Start
- `uv sync` installs all deps
- Server: `uv run uvicorn tukey.server.app:create_app --factory --reload`
- **FIXED**: .env now loaded via `python-dotenv` on server startup
- **Gap**: No CLI entry point (`__main__.py` or `[project.scripts]`) — must use manual uvicorn command

### 2. Add a Provider
- Sidebar → "Providers" button → dialog to add/remove providers
- **Working**: Provider CRUD persists to `~/.tukey/config.json`
- **Gap**: No connection test / validation on save

### 3. Create a Room & Add Models
- Create room via sidebar, click "Configure" → "Add Model"
- **FIXED**: Model ID field now shows hint text explaining `openai/` prefix format
- **Gap**: No model discovery dropdown — user must know the LiteLLM model ID

### 4. Send a Prompt (Response Comparison)
- Type prompt, Enter → fan-out to all models in parallel
- **FIXED**: WebSocket streaming now connected — responses stream in real-time per-model
- **FIXED**: Falls back to HTTP if WebSocket disconnects
- **FIXED**: WebSocket duplicate persistence bug eliminated — turns saved once from streamed results

### 5. View Response Metadata
- ResponseCard shows: tokens in/out, duration, tok/s, cost
- **Working**: Cost shows $0 for models not in LiteLLM's pricing DB (documented limitation)

### 6. Configure Models Independently
- System prompt and temperature slider work per-model
- **Gap**: max_tokens and top_p have no UI controls (data model supports them)

### 7. Multi-turn Conversation
- Messages persist to `messages.jsonl`, history reconstructed per-model
- **Working end-to-end**

### 8. Close & Reopen
- Room list, model configs, and messages all persist and reload
- **Working end-to-end**

### 9. Error Handling
- **FIXED**: Model errors now preserve the correct model_id (was "unknown")
- **Gap**: Raw error strings shown in response card — no user-friendly formatting

### 10. Inspect Raw Data
- Files at `~/.tukey/chatrooms/{uuid}/messages.jsonl` and `meta.json`
- **Working**: Human-readable, user owns files
- **Gap**: No UI indication of data directory path

---

## User Story Coverage

| Story | Status | Notes |
|-------|--------|-------|
| US1.1 API config & model selection | **Partial** | Working but no model discovery UI |
| US1.2 Config persistence | **Working** | .env loaded, providers persist to JSON |
| US1.3 Chat persistence | **Working** | Rooms, models, messages all persist |
| US1.4 Response comparison | **Working** | Parallel fan-out with streaming |
| US1.5 Search | Deferred | Per plan |
| US2.1 Independent config | **Partial** | System prompt + temperature; missing max_tokens/top_p UI |
| US2.2 Broadcast config | Deferred | Per plan |
| US3.1 Data sovereignty | **Working** | All data in ~/.tukey/, no cloud sync |
| US3.2 Import/export | Deferred | Per plan |
| US3.3 Reproducibility | Deferred | Per plan |
| US3.4 Response metadata | **Working** | Tokens, cost, duration, tok/s displayed |
| US4 Python SDK | Deferred | Per plan (module architecture supports it) |
| US5.x Experiments | Deferred | Per plan |
| US6 Synthesizer | Deferred | Per plan |

---

## Bugs Fixed This Session

| # | Issue | Fix |
|---|-------|-----|
| 1 | .env never loaded — server ignored OPENAI_API_BASE/KEY | Added `dotenv.load_dotenv()` in app factory |
| 3 | WebSocket streaming dead code — UI only used HTTP | Wired `useChat.connect()` in ChatRoom, WS connects on room select |
| 4 | WebSocket duplicate persistence — turns saved twice | Rewrote WS handler to collect streamed results and persist once |
| 5 | Model ID field had no format hints | Added helper text explaining `openai/` prefix convention |
| 6 | Error responses lost model_id (stored as "unknown") | Fixed `send_message` to use `models[i]["id"]` from gather index |

## Remaining Gaps

| # | Issue | Severity |
|---|-------|----------|
| 2 | No CLI entry point — manual uvicorn command required | Low |
| 7 | No max_tokens / top_p UI controls | Low |
| 8 | No data directory path shown in UI | Low |
| 9 | Raw error strings in response cards | Low |
| 10 | No model discovery / available models list | Medium |
| 11 | No provider connection test on save | Low |
