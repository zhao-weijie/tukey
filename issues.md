## 2026-05-03 goal gap triage from frontend smoke

This ranking is against `2026-05-03_goals.md`, not against general product quality. Some lower-ranked issues are real bugs or polish gaps, but they are not necessarily critical path for the May 3 goals.

Parallelization note: the two P0 items below are intended to be tackled independently. Keep the Codex live-eval path text-only and agent/discovery-focused. Keep the multimodal path focused on browser image input/output UX. Coordinate only before changing shared run, output, content-block, or artifact API schemas.

### P0 critical path: Codex-driven live evaluation path is not productized
Related goals:
- Must have: "Codex (the agent) - driven evaluation case that can complete in <3 minutes live."
- Must have: "Skill or plugin that enables Codex agent to discover tukey and use its features easily."
- Nice to have: live eval comparing GPT5.5 against a frontier open-source OpenRouter model.

Observed status: a tiny browser-driven text fan-out can be completed manually in under 3 minutes if providers/config sets already exist, but there is no packaged Codex workflow, Tukey skill/plugin, guided command, or ready eval script that an agent can discover and run without inspecting the repo/API.

Why it matters: this is one of the core demos in the goals doc. The current app proves the substrate works, but the agent-facing happy path is still implicit.

Existing issues:
- `(feature) Codex-driven live evaluation path under 3 minutes`
- `(feature) Codex skill/plugin for Tukey discovery and operation`
- `(usability) Agent-driven eval/run workflow is not yet reviewable in the frontend`
- `(usability) Configuration preflight is too shallow for automated runs`

Recommended next slice: create a small blessed workflow that selects or creates a config set, runs 2-4 prompts, reports outputs/metadata, and leaves reviewable run-chain records in the UI. Package its instructions in a Codex skill or plugin.

Parallel boundary:
- Owns: text-only agent workflow, Codex-discoverable instructions/skill/plugin, small run-native API happy path, reviewable run-chain records.
- Avoids: image upload, artifact rendering, image-edit UI, multimodal executor behavior.
- Shared contract: use existing `/api/runs` and `/api/runs/{run_id}/execute`; do not change run/output schemas without coordinating with the multimodal workstream.

### P0 critical path: multimodal is backend-ready but not frontend-reviewable
Related goal:
- Must have: "Add multimodal completions e.g. image editing and generation."

Observed status: backend task types and artifact storage exist, and config slots expose `image_generation` / `image_edit`. The visible frontend still has no image upload/attachment control for image editing, no first-class image prompt/run input flow, and image outputs render as placeholder text instead of displaying artifact content.

Why it matters: the must-have says multimodal completions, and a demo user will judge this in the browser. Backend-only support is not enough for a product demo unless the demo is explicitly API-only.

Existing issue:
- `(feature) Add multimodal completions for image generation and editing`

Recommended next slice: add image output rendering via `/api/artifacts/{artifact_id}/content`, then add minimal image input attachment for `image_edit`. A basic gallery/review surface is more important than advanced annotation in the first pass.

Parallel boundary:
- Owns: image artifact rendering, minimal image input attachment for `image_edit`, browser usability for `image_generation` and `image_edit`.
- Avoids: Codex skill/plugin work, text-only agent eval scripts, eval-plan/synthesis/scheduled-monitoring work.
- Shared contract: preserve existing run/output/content-block/artifact API shapes unless a concrete UI blocker requires a coordinated schema change.

### P1 important: chained-run UI exists but not DAG/progressive-disclosure management
Related goals:
- Must have: runs/configs primitives with chained runs replacing chat sessions.
- Should have: "New UI to manage chained runs (directed acyclic graphs with progressive disclosure on nodes)."

Observed status: the app now uses tasks, config sets, run chains, runs, and outputs in the main UI. The visible chain view is still a mostly linear conversation with arrows. It does not expose branches, selected-output continuation, per-slot lineage mapping, or node-level progressive disclosure.

Why it matters: the main data-structure redesign goal is substantially met, but the "directed acyclic graph" management goal is not. This is less blocking than the Codex and multimodal demos, because the current linear chain can still demonstrate the new primitives.

Existing issues:
- `(redesign) Replace chatrooms and experiments with tasks, config sets, runs, and chained runs`
- `(design) New UI for config sets and chained runs`
- `(improvement) Stack past run responses instead of showing all ResponseCards`

Recommended next slice: implement selected-output continuation first, then surface lineage/branches progressively in the run block UI. Avoid a full graph editor unless branching becomes genuinely hard to understand.

### P1 important: onboarding/docs still describe legacy chatrooms
Status: addressed in README/CLAUDE docs cleanup.

Related goal:
- Must have: "Easy deployment/discovery/onboarding for Codex users (one command line, <1 minute to first run)."

Observed status: the app has guided setup and `uv run tukey` works locally, but `README.md` still describes chatrooms, experiments, legacy search/import/export, and `/api/chat/*` examples. That undercuts discoverability for humans and agents.

Resolution notes: `README.md` now documents tasks, config sets, immutable config versions, runs, run chains, run-native search/export, and the active `/api/runs/{run_id}/execute` flow. `CLAUDE.md` now has a current-product-contract warning above the historical exploration dump so agents do not treat stale chatroom notes as authoritative.

Why it matters: the browser flow is moving in the right direction, but stale docs make the run-native redesign hard to discover and can send Codex down legacy routes.

Existing issue:
- `(feature) One-command onboarding for Codex users`

Recommended next slice: update README quickstart and REST example to tasks/config sets/runs/run chains. Add a "Codex quick path" section that maps directly to the planned skill/plugin.

### P2 useful: frontend run-chain polish gaps
Related goals:
- Must have: UI designed/improved with ChatGPT Image 2.
- Should have: new UI to manage chained runs.

Observed status from browser smoke:
- Config editor can overflow horizontally and clip the second slot at normal in-app browser width.
- After a run completes, the view does not auto-scroll to the newly created run, so fresh results can be below the viewport.
- Search icon has no accessible label; `Ctrl+K` did not open search in the in-app browser attempt, though clicking the icon did.
- Search briefly shows "No results" during debounce before results appear.
- A queued run with no outputs appears inline without enough explanation or recovery affordance.

Why it matters: these affect confidence and demo smoothness, but they do not block proving the run-native substrate or text fan-out.

Existing issues:
- `(design) New UI for config sets and chained runs`
- `(improvement) Response card layout and comparison UX`
- `(improvement) Run input box and default conversation-view width for user inputs should be narrower and centered.`
- `(legacy bug) Having more than 3 model configurations expands the right panel container beyond the visible screen area` is legacy, but the new config editor has a similar overflow family of problem.

Recommended next slice: fix auto-scroll and image rendering first if demo polish matters. Defer deeper layout redesign until the next visual-design pass.

### P3 not critical path for May 3 goals
Related goals:
- Nice to have: OpenRouter new-model monitoring.
- Nice to have: live GPT5.5 vs frontier open-source model in pi-mono.

Observed status: no visible scheduled monitoring UI or ready-made model-comparison demo was found during the smoke test.

Why it matters: these are nice-to-have in the goals doc. Do not let them preempt the P0 Codex workflow and multimodal UI unless the demo explicitly shifts toward model monitoring.

Existing issues:
- `(feature) Codex-driven live evaluation path under 3 minutes`
- Scheduled monitoring is covered in `requirements.md` but should get its own implementation issue when it becomes a near-term slice.

## (legacy bug) Having more than 3 model configurations expands the right panel container beyond the visible screen area
Severity: Major

Impact: Unable to access "Hide Config" button in the current pre-redesign chatroom UI. Expected behavior: Model configurations that overflow behave similarly to ResponseCarousel which allow horizontal scrolling. The top bar that contains the "Hide Config" button and the chatroom/chat name needs to strictly fill only the available screen width (after accounting for the left sidenav).

Decision: this is superseded if the config-set/run-chain redesign lands first. Do not spend significant time fixing the legacy chatroom layout unless it blocks near-term demos.

## (bug) Clicking the "Browse" button in the DirectoryDialog displays a "failed to fetch" error
Severity: Major
Looking at the server console revealed this error

```
*** Terminating app due to uncaught exception 'NSInternalInconsistencyException', reason: 'NSWindow should only be instantiated on the main thread!'
*** First throw call stack:
(
        0   CoreFoundation                      0x000000018585d8ec __exceptionPreprocess + 176
        1   libobjc.A.dylib                     0x0000000185336418 objc_exception_throw + 88
        2   CoreFoundation                      0x0000000185878ec4 _CFBundleGetValueForInfoKey + 0
        3   AppKit                              0x000000018a8fed0c -[NSWindow _initContent:styleMask:backing:defer:contentView:] + 260
        4   AppKit                              0x000000018a8ff114 -[NSWindow initWithContentRect:styleMask:backing:defer:] + 48
        5   libtk8.6.dylib                      0x00000001086306bc TkMacOSXMakeRealWindowExist + 592
        6   libtk8.6.dylib                      0x0000000108630308 TkWmMapWindow + 96
        7   libtk8.6.dylib                      0x000000010858982c MapFrame + 96
        8   libtcl8.6.dylib                     0x000000010849f650 TclServiceIdle + 72
        9   libtcl8.6.dylib                     0x000000010847cf58 Tcl_DoOneEvent + 268
        10  libtk8.6.dylib                      0x0000000108621618 TkpInit + 792
        11  libtk8.6.dylib                      0x0000000108581f7c Initialize + 2368
        12  _tkinter.cpython-311-darwin.so      0x00000001005fa57c Tkapp_New + 936
        13  _tkinter.cpython-311-darwin.so      0x00000001005f9fb8 _tkinter_create + 624
        14  libpython3.11.dylib                 0x00000001017f16fc cfunction_vectorcall_FASTCALL + 80
        15  libpython3.11.dylib                 0x00000001015cec90 _PyEval_EvalFrameDefault + 183844
        16  libpython3.11.dylib                 0x000000010170f664 _PyFunction_Vectorcall + 472
        17  libpython3.11.dylib                 0x00000001017f935c slot_tp_init + 276
        18  libpython3.11.dylib                 0x00000001017fc5d0 type_call + 136
        19  libpython3.11.dylib                 0x00000001015cf18c _PyEval_EvalFrameDefault + 185120
        20  libpython3.11.dylib                 0x000000010170f664 _PyFunction_Vectorcall + 472
        21  libpython3.11.dylib                 0x00000001015d2dd4 _PyEval_EvalFrameDefault + 200552
        22  libpython3.11.dylib                 0x000000010170f664 _PyFunction_Vectorcall + 472
        23  libpython3.11.dylib                 0x00000001017dc1fc method_vectorcall + 340
        24  libpython3.11.dylib                 0x000000010185bff0 thread_run + 220
        25  libpython3.11.dylib                 0x0000000101d0cac8 pythread_wrapper + 48
        26  libsystem_pthread.dylib             0x0000000185771c08 _pthread_start + 136
        27  libsystem_pthread.dylib             0x000000018576cba8 thread_start + 8
)
libc++abi: terminating due to uncaught exception of type NSException
```

## (bug) WR-001 Search results can be non-navigable for valid run-chain members
Severity: Major

Status: resolved in the run-native search/navigation slice.

Problem: run-chain detail/export includes members from `root_run_id`, direct `run.chain_id`, and run-chain edges, but search currently derives result `chain_id` only from `run.chain_id`. Runs created first and later attached as a chain root or edge can appear in chain detail/export while their run/input/output/annotation search results have no `chain_id`. The current SearchDialog closes after selection even when it cannot load a chain, so those results are effectively dead clicks.

Decision: treat run-chain membership as multi-valued for search navigation. Direct `run.chain_id`, `run_chain.root_run_id`, and edge parent/child references are all membership evidence with no hidden primary-chain precedence. For each run/input/output/annotation match, return one result per visible non-archived chain context with `chain_id` and `chain_name`. If no visible chain context exists, omit the match from the chain-oriented search UI until a standalone run view exists.

Implementation notes:
- Build or share a helper that derives run-to-chain contexts using the same membership semantics as run-chain detail/export.
- Avoid silently picking the first matching chain when a run belongs to multiple chains.
- Cache chain metadata while building search results so repeated matches do not repeatedly read the same chain files.
- Update the search UI to make duplicate matches under different chain names understandable.
- Add regression coverage for root-only membership, edge-only membership, multiple-chain membership, archived-chain exclusion, and no-chain omission.

## (redesign) Replace chatrooms and experiments with tasks, config sets, runs, and chained runs
Priority: high

Problem: chatrooms are a thin container around the things Tukey actually cares about: reusable model/tool/prompt configurations, execution records, outputs, annotations, and lineage. They make model configs feel like mutable chat-local UI state, which is bad for reproducibility and traceability. It is like losing the methodology and experiment conditions of a scientific experiment.

Decisions:
- Kill chatrooms as a product/data primitive. No migration support is required.
- Kill experiments as an execution/data primitive. Formal evals should be a workflow over runs, not a separate run engine.
- Support exploratory comparison, formal evals, and agent/cron-driven monitoring with the same run substrate.
- Use user-facing vocabulary around **task**, **use case**, **eval**, **config set**, **run**, and **run chain**.

Target model:
- **Task / Use Case**: optional organizing object for what the user is trying to evaluate, such as "support email triage" or "invoice field extraction".
- **Config Set**: reusable collection of model/config slots. A slot includes provider route, model ID, display name, system prompt, sampling params, response format, tools, MCP servers, and any provider-specific extra params.
- **Config Version**: immutable snapshot of a config slot once used. Used versions are append-only and must remain recoverable even if the active config set is edited, archived, or deleted from the visible UI.
- **Run**: execution of one prompt/test case/prompt set against one config set. A run records exact config versions, inputs, outputs, metadata, cost, latency, errors, annotations, and selected/pinned responses.
- **Run Chain**: chat-like continuation built by linking a run to selected outputs from prior runs. A chain can look like a chat in the UI, but its data model should preserve per-model/per-response lineage instead of a vague shared chat history.
- **Eval Plan**: optional planning object for durable criteria, test cases/prompt sets, config sets, and schedules. It creates or groups runs but is not an execution primitive.
- **Schedule**: optional cron/agent automation over a task/eval plan/config set, used for new-model monitoring and recurring evals.
- **View**: UI organization over runs and chains, such as conversation view, comparison grid, eval table, model-monitoring dashboard, or semantic similarity grouping.

Requirements:
- Chats/sessions should become a view over chained runs, not their own persistence primitive.
- Follow-up runs must be able to continue from different selected response variants per model/config slot.
- Deleting/removing a config from the active UI must never delete a config version that has been used by any run.
- Exploratory comparisons, formal evals, scheduled evals, and agent-driven runs should use the same run/config-set primitives.
- Eval plans are optional orchestration/grouping objects. They must not contain a second execution path.
- Refer to `SUS8` in `requirements.md`.

## (improvement) Allow per-config-slot manual retries and additional responses
Priority: high
Problem: Some models fail while others succeed sometimes due to model quality or API/provider issues. It is not currently possible to retry just for the failed models.

The first successful response should be shown as default.

## (feature) Add multimodal completions for image generation and editing
Priority: high
Problem: Tukey currently centers text completions, but model evaluation increasingly includes image generation/editing and other multimodal outputs. Users need to compare multimodal providers/models with the same reproducibility guarantees as text runs.

Desired behavior: runs can include multimodal inputs and outputs, including image generation and image editing. Outputs should be stored locally, linked from run records, and reviewable/annotatable in the UI.

Status: backend implementation complete on `codex/run-multimodal-contract`.

Delivered:
- Run input content blocks preserve text plus image/artifact inputs through provider calls instead of collapsing to plain text.
- Artifact image inputs resolve to provider-compatible data URLs at execution time.
- `image_generation` and `image_edit` task types dispatch through the run engine.
- OpenAI-compatible native image generation uses `/images/generations`.
- OpenAI-compatible native image editing uses multipart `/images/edits`.
- OpenRouter image generation/edit-compatible flows use multimodal `/chat/completions`.
- Generated/edited image bytes are persisted as run artifacts and referenced from `RunOutput.content`.
- Provider image parsing accepts `b64_json`, base64 `data:` URLs, and hosted HTTPS image URLs with image content-type validation.

Remaining:
- Frontend rendering/review affordances for image artifact outputs are still needed for a full product experience.
- Run-chain DAG validation remains a separate follow-up and is not part of the multimodal backend branch.

## (feature) Codex-driven live evaluation path under 3 minutes
Priority: high
Problem: Tukey's agent-driven value proposition needs a short, reliable demonstration where Codex can discover Tukey, create or select a config set, run a small evaluation, and summarize/review results live.

Desired behavior: provide one happy-path agent workflow that completes in under 3 minutes on a local machine, using a small prompt/test set and a small config set. The workflow should exercise config sets, runs, outputs, metadata, and review/summary surfaces.

## (feature) Codex skill/plugin for Tukey discovery and operation
Priority: high
Problem: Codex should be able to discover Tukey's capabilities and use them without reverse-engineering the repo or REST API each time.

Desired behavior: provide a Codex skill or plugin that documents Tukey's core concepts, available commands/API paths, common workflows, and safe defaults for local evaluation runs.

## (feature) One-command onboarding for Codex users
Priority: high
Problem: Tukey needs easy deployment/discovery for agent users. A new Codex user should get from install to first meaningful run in under one minute.

Desired behavior: provide a one-command path that installs/starts Tukey, verifies provider setup or guides quick setup, and creates a minimal first config set/run. Current PyPI distribution can remain, but alternatives should be considered if they reduce time-to-first-run.

## (design) New UI for config sets and chained runs
Priority: high
Problem: Replacing chatrooms requires a UI that can show config sets, runs, and run chains without overwhelming users. A raw DAG editor is likely too heavy for the primary surface.

Desired behavior: design a conversation-like chained-run view with progressive disclosure. The main path should feel like chat/comparison; lineage, branches, retries, and selected-response dependencies should be available on demand. Use ChatGPT Image 2 or equivalent visual design support to explore layouts before implementation.

## (improvement) More flexible model/provider/config in a particular configuration "slot" instead of deleting
Priority: normal

## (improvement) Tool Choice and Response Format options in config slots do not have a "broadcast" option
Priority: normal
## (improvement) Allow individual response cards to be expanded in width for easier reading of long responses
Priority: high

As a user I want to be able to expand individual response cards to make it easier to read long responses.  

## (improvement) Response card layout and comparison UX
Priority: normal

As a user I want to be able to choose which response cards are next to each other so that I can easily compare 2 models' responses side by side.

As a user I want to choose which response cards are currently visible so that I can focus on comparing the responses I care about most.

## (improvement) Stack past run responses instead of showing all ResponseCards
Priority: normal

Idea: stack and show only the first pinned response or the one with the most positive annotations for past runs in a chain. Only the current run's responses are shown in full. This reduces visual clutter. The user gets a button to expand the full Response Carousel to full width.

Related idea: this might work well together with horizontal stack-ranking where the user drags conversation ResponseCards to rank them horizontally. Drag handle rather than the entire ResponseCard component as target should be easier to use.


## (improvement) Run-chain stats for per-config-slot metadata
Priority: normal
As a user I want a quick view of how each model/config slot performed across a run chain so that I can decide which one to use as default or promote into a new config set.
When hovering the run-chain name in the top bar, a popover/dropdown appears showing the stats for each model/config slot.

Stats to include: cost, input tokens, output tokens, latency, tok/s, user ratings (positive + negative).

## (improvement) Run input box and default conversation-view width for user inputs should be narrower and centered.
Priority: normal
As a user I want the input and message area in the chained-run conversation view to be centered in my view so that my eyes do not have to scan left and right too much, reducing eye fatigue.

Multiple model responses are allowed to take the full width of the run view container, since it is easier to compare responses side by side.

![Sceenshot](./.testing_images/centered_chat.png)

## (usability) Agent-driven eval/run workflow is not yet reviewable in the frontend
Priority: high
Problem: The requirements describe agents/scripts driving statistically meaningful batches while domain experts review and annotate results in the same product. The current backend experiment API is a legacy pre-redesign implementation path; the target architecture should expose agent-driven work as runs and optional eval plans. Batch eval results, chained runs, and annotations are not exposed in the UI, so a human reviewer must inspect API/raw files instead of staying in the browser.

Related gaps:
- Legacy experiment runs are synchronous and opaque: no progress stream, cancel, retry, resume, or per-case status.
- Legacy experiment execution launches all test-case/model pairs concurrently, which makes rate limits and cost control hard for agent-driven runs.
- REST run execution cannot request multiple completions or pass response-index context, even though the WebSocket path can.
- Multi-turn response selection is turn-level rather than per-model/config slot, so different models cannot cleanly continue from different selected completion variants.

## (usability) Configuration preflight is too shallow for automated runs
Priority: high
Problem: Before an agent spends time and money on a batch, Tukey should validate the exact selected provider/model/config combination. Current checks are partial: provider testing uses a hardcoded model, gateway/custom models may have unknown capabilities, and invalid JSON schema/tool config can be silently ignored while typing.

Desired behavior: provide a preflight summary that checks each selected model ID, provider route, model capability assumptions, response format, tool configuration, MCP availability, token limits, and estimated cost/rate-limit risk before running a batch.

---
# Not relevant to the codebase, for reference only
## (bug) Antigravity bug

Symptom: Open repo in antigravity, type a prompt and send in both planning and fast mode. Switched to other repository, no change. Switched to agent manager, chat is not created. No response or thinking or any output at all. Same result even after downloading and installing latest version.

---

# RESOLVED

## (bug) Replacing expired key breaks existing configurations
### Severity: Major
Problem: When a key expires, a provider has to be deleted for the new key to be added and the existing configurations break.

Proposed Solution: Add an "edit" feature for keys so that we can replace the key without deleting the provider. Warn user when removing providers about potential effects with a focus modal overlay plus confirm or cancel button choices.

## (bug) Tool call element in ResponseCard.tsx is duplicated in streaming status

Symptom: tool call element is duplicated once (2 elements per tool call) shown when streaming results. When streaming finishes, the extra tool calls disappear.

## (bug) dialog.tsx elements overflow the container when state changes

Symptom: Elements fit within the container width on first load. However, after Searching (for the SearchDialog) and Testing (for the Mcpserversetup), the buttons and text input boxes bleed past the right boundary of the container.

![Sceenshot](./.testing_images/dialogbug.png)

## (bug) Navigating away from a streaming chat, then returning results in a blank screen
Severity: Major

Start a new chat in a configured chatroom; send a message; navigate to another chat when first token has not arrived yet; navigate back; blank screen instead of in-progress stream observed - does not even have user message.

In fixing this bug, more issues were created. If there is a single error-ed response, the Response Cards are repeated below and remain in the "Streaming..." state.

## (improvement) Resume streaming after navigating away and back
Priority: high
Problem: When a user navigates away from a chat mid-stream and returns, they see skeleton placeholders instead of live streaming. The backend continues streaming (in-flight tasks run to completion), but the new WebSocket connection cannot receive those chunks.

Proposed solution: Add a module-level stream registry in `websocket.py` that maps `(chatroom_id, chat_id)` to a mutable sender reference + accumulated content per model. When a new WebSocket connects to a chat with an active stream: (1) swap the sender so in-flight tasks send chunks to the new connection, (2) send a `stream_resume` catch-up message with all content accumulated so far, (3) continue streaming live. Frontend handles the new `stream_resume` message type by populating `streaming` state with accumulated content. ~40 lines backend, ~10 lines frontend.
