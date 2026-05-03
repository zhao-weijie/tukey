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
