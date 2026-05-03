# Tukey
A performant, simple, local-first application for empirically selecting the best LLMs, configurations, and system prompts for a task or use case, replacing vibes-based model selection with reproducible, statistically grounded evals that technical and non-technical team members can run and judge together.

## Key Features
- Reusable evaluation primitives. Config sets define what is being tested; runs record what happened; chained runs provide a chat-like workflow without making chat sessions the underlying data model.
- Local persistence, total ownership. Eval data stays on owned hardware. Delete it, copy it, transfer it anytime.
- Scientific rigour over gut feel. Run statistically significant test suites programmatically, not one-shot manual comparisons.
- Shared ground truth. Domain experts and developers work from the same config sets, runs, annotations, and outputs — not separate tools with incomparable results.

## Design principles

### Decision frame before data
Every formal eval should begin with an explicit decision frame: what task or use case is being decided, what criteria matter, and who is judging. Criteria should be defined before outputs are reviewed, not after, otherwise evaluators anchor on whichever model sounds most confident. This is lightweight by design, not a bureaucratic gate.

### Three families of evaluation criteria
Tukey surfaces functional criteria (did the model do the thing?), quality criteria (how well did it do the thing?), and operational criteria (what did it cost?) as distinct dimensions. These frequently conflict — the most accurate model may be the slowest and most expensive — and collapsing them into a single score is where vibes-based selection sneaks back in.

### Statistical honesty
Tukey should never let users draw conclusions from insufficient evidence. Results are presented with visibility into discordant pairs, sample sizes, and statistical significance. When results are inconclusive, the product says so rather than presenting misleading pass rates.

### Domain grounding over developer convenience
Programmatic test generation is powerful but dangerous without domain expert involvement. The product should make it easy — and natural — for domain experts to participate in test case design, annotation, and criteria definition, not just review.

## Target architecture

Tukey's core primitives are **config sets**, **immutable config versions**, **runs**, and **run chains**. Chatrooms and experiments are retired as target product/data primitives; no migration support is required for the redesign.

### Architecture decisions
- Runs are the only execution primitive. Exploratory comparisons, formal evals, agent-driven batches, scheduled monitoring, retries, and chat-like continuations all create runs and outputs through the same run engine.
- Eval plans are optional orchestration objects. They may hold criteria, test cases/prompt sets, config sets, and schedules, but they must not introduce a second execution path.
- Run chains are lineage plus view state. They make exploratory work feel chat-like while preserving per-slot/per-output dependencies.
- Tasks/use cases are user-facing organization. They help users think in the language of "what am I evaluating?" rather than "which backend object am I using?"
- Agents and cron jobs should use the same public contracts as the UI.

### Rationale
Supporting exploratory comparison, formal evals, and agent-operated monitoring does not require separate primitives. The underlying objects are the same: configs, inputs, outputs, annotations, metadata, and lineage. Keeping one run substrate avoids today's split between chatrooms and experiments, while still allowing polished workflows for exploratory-to-formal progression.

### Config sets
A config set is a reusable collection of model/config slots. Each slot captures provider route, model ID, display name, system prompt, sampling params, response format, tools, MCP servers, and provider-specific extra params. Users can edit active config sets freely, but once a slot is used its resolved config is recorded as an immutable config version.

### Runs
A run executes one prompt, test case, or prompt set against a config set. It records the exact config versions used, all inputs, all outputs, response metadata, costs, latency, errors, annotations, and selected/pinned responses. Interactive comparisons, structured evals, scheduled evals, and agent-driven batches use the same run primitive.

### Run chains
A run chain links runs together so the UI can resemble a chat when that is the most natural workflow. A follow-up run can continue from selected outputs from previous runs, including different selected response variants per model/config slot. The chain records lineage explicitly instead of relying on a vague shared conversation history.

### Views
Views organize config sets, runs, and run chains for different jobs: conversation view, comparison grid, eval table, model-monitoring dashboard, semantic similarity grouping, or agent-driven review queue. Views are presentation, not persistence primitives.

### Optional eval plans
An eval plan is a thin workflow object for durable criteria, test cases/prompt sets, config sets, and schedules. It is useful for extraction tasks, F1/scored tasks, recurring new-model checks, and team review, but exploratory work does not need one. A run chain can later be promoted into an eval plan by selecting prompts, outputs, criteria, and config sets; the existing runs stay unchanged.

## Near-term priorities

- Multimodal runs: support image generation and image editing as first-class run outputs with local artifact storage and UI review.
- Agent-driven evaluation: provide a Codex-driven happy path that can complete a meaningful local evaluation in under 3 minutes.
- Codex discoverability: provide a skill or plugin that lets Codex understand Tukey's concepts, commands, API surface, and safe workflows.
- Onboarding: support one-command setup/start and aim for under 1 minute to first local run for Codex users.
- Chained-run UI: replace chatroom UI with config-set and run-chain management using progressive disclosure for DAG structure.
- Scheduled evals: support cron/agent workflows for checking newly available models and running selected tasks without hardcoded model IDs.

## Implementation status

Note: implementation status below describes the current pre-redesign app. Chatroom/chat/experiment references are legacy implementation facts, not target primitives.

### Complete
- US1.1 API configuration and model selection — provider CRUD, model ID entry, model-aware config (capabilities endpoint)
- US1.2 Configuration persistence — API keys and configs saved to ~/.tukey/
- US1.3 Chat persistence — chatrooms persist models, configs, and conversation history
- US1.4 Response comparison — parallel fan-out with streaming, side-by-side display, multiple completions per model (n=1–9), per-model response cycling, additive regeneration
- US1.5 Search — full-text search across chatrooms, chats, and messages via /api/search
- US2.1 Independent configuration — system prompt, temperature, max_tokens, top_p, reasoning_effort (conditional on model capabilities)
- US2.2 Broadcast configuration — "Apply to all" per field across models in a chatroom
- US3.1 Data sovereignty — all data in ~/.tukey/, no cloud sync
- US3.2 Chat import/export — per-chatroom JSON export/import via sidebar and REST endpoints
- US3.3 Experiment reproducibility — manifest endpoint, chat replay, full input recording
- US3.4 Response metadata — tokens in/out, cost, duration, tok/s per response (toggle via ChartBar icon)
- US4 Programmatic interface — TukeyClient SDK (httpx), provider/chatroom/chat/message CRUD, run_batch, manifest, replay
- UX: Responsive sidebar — overlay drawer on small screens (<768px) with backdrop, auto-close on selection
- UX: Delete confirmations — browser confirm dialog before deleting chatrooms or chats
- UX: Loading skeleton — pulsing placeholder cards shown between send and first streaming chunk
- UX: Welcome flow — guided setup renders within the chat area (sidebar visible) instead of a full-screen takeover; "I already have API keys" opens the existing ProviderSetup dialog; OpenRouter quick-start flow creates provider + sample chatroom in one step
- UX: Native folder picker — data directory selection uses the system file dialog (tkinter) instead of manual path entry
- Fix: Custom OpenAI-compatible gateway — correct SSE parsing, finish_reason handling, stream_options support, strip model prefix before sending to API
- SUS6 Copy responses — copy full response (button in card header) and copy individual fenced code blocks (hover button)
- SUS7 Improve readability — LLM responses rendered as markdown (headings, lists, tables, code blocks with syntax highlighting); user message newlines preserved via whitespace-pre-wrap

- US5.2 Human annotation (chat) — text-range annotation on chat response cards: select text → rate (thumbs up/down) + comment → highlights persist to backend (annotations.jsonl). Schema uses W3C-aligned nested target (target.source + target.selector with TextQuoteSelector). Annotations included in chatroom export/import. Covers US5.2.2–5.2.8. US5.2.1 replaced with automatic popover on selection; US5.2.9 deferred.

### In progress
- Legacy US5.1, 5.3, 5.4 Experiment framework — backend complete (experiment CRUD, test cases, run execution with multi-turn + concurrency, annotations, summary, REST API, SDK). Frontend UI not yet built.

### In progress
- Legacy US6 Synthesis — data contract (`ExperimentBundle`) and tool protocol (`SynthesisTool`) complete. Built-in tools (`basic_stats`, `tfidf`) working. CLI supports both chatrooms and experiments. Frontend UI not yet built. Target redesign should replace this source contract with a run-native bundle.

### Not started
- SUS1–SUS5 Stretch stories (except SUS6, SUS7)

## Core user stories

### US1.1 API configuration and model selection
As a user, I want to select any model from the multiple APIs I have access to so I can chat with GPT, Claude, Gemini, DeepSeek, Llama, and others from a single interface.

### US1.2 Configuration persistence
As a user, I want my API keys and configurations to be saved so that I can re-use them easily and do not have to re-enter them every time.

### US1.3 Config set persistence
As a user, I want reusable config sets to persist which model/config slots are included, including provider routes, model IDs, system prompts, parameters, tools, and response formats, so I can reopen or reuse an evaluation setup without reconstructing it.

### US1.4 Run-based response comparison
As a user, I want to run a prompt once against every slot in a config set so I get parallel responses for comparison without copy-pasting.

### US1.4a Multiple completions
As a user, I want to generate N completions (1–9) per model per prompt so that I can observe response variance and make statistically meaningful comparisons rather than drawing conclusions from a single sample.

### US1.4b Additive regeneration
As a user, I want to generate additional completions for a completed turn — appended to the existing responses, not replacing them — so I can increase my sample size after reviewing initial results.

### US1.4c Response cycling
As a user, I want to cycle through multiple completions per model independently (< 1/3 >) so I can compare responses within a model as well as across models.

### US1.4d Chained-run context selection
As a user, I want follow-up runs to use whichever prior response variant I selected for each model/config slot so that chained runs branch from the outputs I chose, not always the first response.

### US1.5 Search
As a user, I want to search across config sets, runs, run chains, prompts, responses, and annotations so I can find prior evaluation work without scrolling.

### US2.1 Independent configuration
As a user, I want to configure each slot in a config set independently (system prompt, temperature, provider routing, tools, response format, etc.) so I can compare how the same prompt performs under different settings, or tune each model to its strengths.

### US2.2 Broadcast configuration
As a user, I want to optionally apply a configuration change to all slots in a config set simultaneously so I don't have to repeat the configuration across every model when I want a consistent baseline.

### US3.1 Data sovereignty
As a user, I want all config sets, runs, run chains, responses, and annotations stored locally on my device so my evaluation history is private and not synced to a cloud provider's servers.

### US3.2 Config set and run import/export
As a user, I want to export and import config sets, runs, run chains, responses, and annotations via the settings menu so I can back up or transfer my evaluation history between devices.

### US3.3 Run reproducibility
As a developer of agentic apps, I want every run to record the complete set of inputs needed to reproduce it exactly: config versions, provider routes, model identifiers, system prompts, tools, test cases, user inputs, raw responses, and operational metadata, so that results can be challenged, replicated, and built upon rather than trusted by feel.

### US3.4 Response metadata
As a user, I want to see per-response metadata — tokens per second, token count, cost, and duration — alongside each model's output so I can factor speed and cost into my model selection decision, not just output quality.

### US4 Programmatic interface
As a developer, I want to drive the exact same config sets, runs, chained continuations, annotations, and analysis using Python scripts or AI agents so that I can run statistically significant numbers of test cases across models without manual input, because a single manually entered prompt is not evidence.

### US5.1 Eval task identity
As a user, I want to save a named task or use case with an optional versioned eval plan comprising a decision frame, test cases, prompt sets, and config sets so that I can share it with colleagues, re-run it after a model update, and compare results over time against a stable baseline.

### US5.2 Human annotation
As a domain expert, I want to review the outputs of a batch eval my technical colleague or agent configured and ran, and record my own pass/fail judgments, severity ratings, and qualitative notes against each response, so that my domain knowledge contributes independent ground truth rather than being anchored by the model's own outputs or a developer's interpretation.

**US5.2.1** Enter annotation mode — As an evaluator, I can toggle "annotation mode" on a response card so that text selection creates annotations instead of default browser selection.
**US5.2.2** Highlight and rate — As an evaluator, I can select a text range in a response, then give it a thumbs up or thumbs down, so I can quickly flag good/bad sections without writing a full comment.
**US5.2.3** Add a comment — As an evaluator, after highlighting and rating, I see a text input popover where I can type a freeform comment and submit it, so I can explain why the section is good or bad.
**US5.2.4** See highlights — As an evaluator, I can see all annotated ranges highlighted in the response body (green for positive, red for negative) so I can scan quality at a glance.
**US5.2.5** Review a comment — As an evaluator, I can click/hover a highlight to see its rating and comment in a popover, so I can review past annotations.
**US5.2.6** Edit/delete an annotation — As an evaluator, I can edit the comment text or delete an annotation entirely from the review popover.
**US5.2.7** Annotation count in action bar — As an evaluator, I can see a badge/counter in the card's action bar showing the number of annotations, so I know at a glance whether a response has been reviewed.
**US5.2.8** Persist annotations — As an evaluator, annotations survive page refresh and are tied to the specific response (model + response index), so I don't lose my work.
**US5.2.9** Navigate between annotations — As an evaluator, I can step through annotations sequentially (prev/next) so I can review them in order without scanning the full response.


**US5.2 Out of scope:**
- Multi-user / collaborative annotation
- Annotation on streaming responses (only completed responses)
- Annotation across response versions (each response index has its own annotations)

### US5.3 Shared evaluation
As a team, we want domain experts and developers to work from the same config sets, run records, test cases, raw outputs, annotations, and metadata so that our conclusions can be compared, reconciled, and trusted as coming from a common source of truth rather than incomparable tools.

### US5.4 Eval brief
As a team lead, I want every formal eval plan to require a lightweight brief stating the decision to be made, the evaluation criteria, and who will judge so that the team aligns on what "good" looks like before seeing any model outputs, preventing post-hoc rationalization.

### US6 Synthesis
As a user, I want to run composable analysis tools against completed runs, run chains, or evaluation plans, including their responses, human annotations, config versions, and metadata, so that I can understand how models differ, identify patterns, and highlight tradeoffs without the tool prescribing which analysis technique to use.

**Design philosophy:** Synthesis is plumbing, not opinion. Different tasks need different analysis — TF-IDF for structured extraction, embeddings for open-ended text, LLM narration for qualitative summaries, generative remix for combining the best elements. Tukey provides:

1. **A data contract** (`RunBundle`) — a structured snapshot of everything an analysis tool needs (responses, annotations, config versions, operational metrics), built from runs, run chains, tasks, and optional eval plans. Tools never touch storage directly.
2. **A tool protocol** (`SynthesisTool`) — any callable that receives a run-native bundle and returns structured `SynthesisResult` sections (text, tables, matrices, JSON). No side effects.
3. **Built-in tools as examples** — `basic_stats` (per-model token/word/cost/latency counts) and `tfidf` (vocabulary-level similarity) ship as reference implementations. They are not privileged — user-defined tools use the same interface.

**What Tukey does not do:** prescribe which NLP technique to use, auto-classify prompt types, declare winners, or collapse distinct evaluation dimensions into a single score.

**All run sources are first-class:** interactive comparisons, chained continuations, agent-driven batches, scheduled checks, and formal eval plans all produce runs with the same analysis surface. The synthesis interface works identically across runs, run chains, tasks, and eval plans.

### US7 Multimodal runs
As a user, I want config sets and runs to support multimodal model capabilities such as image generation and image editing so I can evaluate text, image, and mixed-media models with the same reproducible workflow.

### US8 Agent-ready Tukey
As a Codex user, I want Tukey to expose a clear skill/plugin and one-command local workflow so an agent can discover Tukey, create or select a config set, execute a small run, and summarize the results without me manually wiring every API call or approving every sandbox command.

### US9 Scheduled model monitoring
As a user, I want to schedule recurring evals for selected tasks/config sets so Tukey or an agent can discover new provider models, run the task against candidates I approve or filter for, and compare the results against prior runs.

## Stretch user stories

### SUS1 Tool comparison
As a user, using the same model configuration and system prompts, I want to load different skills/tools/MCPs into multiple config slots in the same config set so that I can quickly identify the best combinations/selections for a given task.

### SUS2 Annotation severity
As a domain expert, I want to record not just pass/fail but the severity of failures (e.g. minor miss, major error, catastrophic) so that a 90% pass rate with two catastrophic failures looks different from a 90% pass rate with two minor misses.

### SUS3 Test suite staleness
As a user, I want the product to flag when a test suite may be stale — for example, when all models pass all cases across consecutive runs — so that I am prompted to update my test cases as the quality floor rises rather than rubber-stamping results.

### SUS4 Criteria templates
As a team, we want access to domain-specific criteria templates (e.g. healthcare agent: empathy, safety, clinical accuracy; code assistant: correctness, conciseness, format compliance) so that we have a starting point for defining what "good" looks like rather than starting from scratch.

### SUS5 Statistical significance surfacing
As a user, I want the product to surface the number of discordant pairs between models and flag when sample sizes are insufficient for statistical conclusions — so that I am not misled by differences that could be noise (e.g. 8/10 vs 6/10 pass rates with only 4 disagreements).

### SUS6 Copying individual responses
As a user, I want a frictionless way to copy responses OR code within fenced blocks to clipboard with a single interaction so that I can use it in a downstream application.

### SUS7 Improve readability
As a user of the webapp, I want my inputs AND model responses to be formatted and rendered in their intended format so that I can read them more quickly. e.g. newlines in my inputs are currently lost, markdown is not rendered. 

### SUS8 Model monitoring
As an AI enthusiast barely keeping up, I want to be able to make quick assessments of new LLMs as soon as possible after their release so that I can update my understanding/evaluation/decisions of which LLMs to use for which tasks. 

As a user of the webapp and backend module, I want to be able to define and re-use sets of configurations and (single-turn) prompts easily across providers and models so that I can automate fan-out evaluation of different models.

As a user of the webapp and backend module, I want to be able to scan providers for new models added since the last run and run predefined config+prompt sets against those I'm interested in so that I can evaluate their performance with minimal effort.

### SUS9 Alternate view/organization of runs by characteristics other than chain
As a user of the webapp, I want to view my runs grouped by some combination of semantic/lexical similarity of configuration, model, prompt, output, and annotation so that I can select responses from the most similar configs for comparison.

Idea: semantic embedding + vector distance, or property graph?
