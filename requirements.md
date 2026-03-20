# Tukey
A performant, simple, local-first application for empirically selecting the best LLMs, configurations, and system prompts for a given task — replacing vibes-based model selection with reproducible, statistically grounded experiments that technical and non-technical team members can run and judge together.

## Key Features
- Local persistence, total ownership. Experiment data stays on owned hardware. Delete it, copy it, transfer it anytime.
- Scientific rigour over gut feel. Run statistically significant test suites programmatically, not one-shot manual comparisons.
- Shared ground truth. Domain experts and developers work from the same experiments, configs, and outputs — not separate tools with incomparable results.

## Design principles

### Decision frame before data
Every experiment should begin with an explicit decision frame: what is being decided, what criteria matter, and who is judging. Criteria must be defined before outputs are reviewed, not after — otherwise evaluators anchor on whichever model sounds most confident. This is lightweight by design (not a bureaucratic gate), but non-optional.

### Three families of evaluation criteria
Tukey surfaces functional criteria (did the model do the thing?), quality criteria (how well did it do the thing?), and operational criteria (what did it cost?) as distinct dimensions. These frequently conflict — the most accurate model may be the slowest and most expensive — and collapsing them into a single score is where vibes-based selection sneaks back in.

### Statistical honesty
Tukey should never let users draw conclusions from insufficient evidence. Results are presented with visibility into discordant pairs, sample sizes, and statistical significance. When results are inconclusive, the product says so rather than presenting misleading pass rates.

### Domain grounding over developer convenience
Programmatic test generation is powerful but dangerous without domain expert involvement. The product should make it easy — and natural — for domain experts to participate in test case design, annotation, and criteria definition, not just review.

## Implementation status

### Complete
- US1.1 API configuration and model selection — provider CRUD, model ID entry, model-aware config (capabilities endpoint)
- US1.2 Configuration persistence — API keys and configs saved to ~/.tukey/
- US1.3 Chat persistence — chatrooms persist models, configs, and conversation history
- US1.4 Response comparison — parallel fan-out with streaming, side-by-side display
- US1.5 Search — full-text search across chatrooms, chats, and messages via /api/search
- US2.1 Independent configuration — system prompt, temperature, max_tokens, top_p, reasoning_effort (conditional on model capabilities)
- US2.2 Broadcast configuration — "Apply to all" per field across models in a chatroom
- US3.1 Data sovereignty — all data in ~/.tukey/, no cloud sync
- US3.2 Chat import/export — per-chatroom JSON export/import via sidebar and REST endpoints
- US3.3 Experiment reproducibility — manifest endpoint, chat replay, full input recording
- US3.4 Response metadata — tokens in/out, cost, duration, tok/s per response (toggle via ChartBar icon)
- US4 Programmatic interface — TukeyClient SDK (httpx), provider/chatroom/chat/message CRUD, run_batch, manifest, replay

### In progress
- US5.1–5.4 Experiment framework — backend complete (experiment CRUD, test cases, run execution with multi-turn + concurrency, annotations, summary, REST API, SDK). Frontend UI not yet built.

### Not started
- US6 Synthesizer
- SUS1–SUS5 Stretch stories

## Core user stories

### US1.1 API configuration and model selection
As a user, I want to select any model from the multiple APIs I have access to so I can chat with GPT, Claude, Gemini, DeepSeek, Llama, and others from a single interface.

### US1.2 Configuration persistence
As a user, I want my API keys and configurations to be saved so that I can re-use them easily and do not have to re-enter them every time.

### US1.3 Chat persistence
As a user, I want a chatroom to persist which models are included, each model's configuration, and each model's conversation history so I can close and reopen a session without losing my setup.

### US1.4 Response comparison
As a user, I want to send a prompt once and have it go to all models in the chatroom so I get parallel responses for comparison without copy-pasting.

### US1.5 Search
As a user, I want to search across saved chatrooms so I can find a prior session without scrolling.

### US2.1 Independent configuration
As a user, I want to configure each model in a chatroom independently (system prompt, temperature, provider routing, etc.) so I can compare how the same prompt performs under different settings, or tune each model to its strengths.

### US2.2 Broadcast configuration
As a user, I want to optionally apply a configuration change to all models in a chatroom simultaneously so I don't have to repeat the configuration across every model when I want a consistent baseline.

### US3.1 Data sovereignty
As a user, I want all my chatroom conversations stored locally on my device so my conversation history is private and not synced to a cloud provider's servers.

### US3.2 Chat import/export
As a user, I want to export and import conversations via the settings menu so I can back up or transfer my chat history between devices.

### US3.3 Experiment reproducibility
As a developer of agentic apps, I want every experiment to record the complete set of inputs needed to reproduce it exactly — model identifiers and versions, full configuration, system prompts, test cases, and raw responses — so that results can be challenged, replicated, and built upon rather than trusted by feel.

### US3.4 Response metadata
As a user, I want to see per-response metadata — tokens per second, token count, cost, and duration — alongside each model's output so I can factor speed and cost into my model selection decision, not just output quality.

### US4 Programmatic interface
As a developer, I want to drive the exact same model selection, configuration, and multi-turn interaction using Python scripts or AI agents so that I can run statistically significant numbers of test cases across models without manual input — because a single manually entered prompt is not evidence.

### US5.1 Experiment identity
As a user, I want to save a named, versioned experiment — comprising a defined set of test cases, model configurations, and system prompts — so that I can share it with colleagues, re-run it after a model update, and compare results over time against a stable baseline.

### US5.2 Human annotation
As a domain expert, I want to review the outputs of a batch experiment my technical colleague configured and ran, and record my own pass/fail judgments, severity ratings, and qualitative notes against each response, so that my domain knowledge contributes independent ground truth rather than being anchored by the model's own outputs or a developer's interpretation.

### US5.3 Shared evaluation
As a team, we want domain experts and developers to work from the same experiment — the same test cases, the same model configs, the same raw outputs — so that our conclusions can be compared, reconciled, and trusted as coming from a common source of truth rather than incomparable tools.

### US5.4 Experiment brief
As a team lead, I want every experiment to require a lightweight brief — stating the decision to be made, the evaluation criteria, and who will judge — so that the team aligns on what "good" looks like before seeing any model outputs, preventing post-hoc rationalization.

### US6 Synthesizer
As a user, I want to select a completed experiment — its transcripts, human annotations, and metadata — and feed it to an LLM synthesizer that describes how responses differ, identifies patterns in failures, and highlights tradeoffs across models — without declaring a winner, so that the team can make the final judgment informed by analysis rather than delegating the decision to a model.

## Stretch user stories

### SUS1 Tool comparison
As a user, using the same model configuration and system prompts, I want to load different skills/tools/MCPs into multiple config buckets in the same chatroom so that I can quickly identify the best combinations/selections for a given task.

### SUS2 Annotation severity
As a domain expert, I want to record not just pass/fail but the severity of failures (e.g. minor miss, major error, catastrophic) so that a 90% pass rate with two catastrophic failures looks different from a 90% pass rate with two minor misses.

### SUS3 Test suite staleness
As a user, I want the product to flag when a test suite may be stale — for example, when all models pass all cases across consecutive runs — so that I am prompted to update my test cases as the quality floor rises rather than rubber-stamping results.

### SUS4 Criteria templates
As a team, we want access to domain-specific criteria templates (e.g. healthcare agent: empathy, safety, clinical accuracy; code assistant: correctness, conciseness, format compliance) so that we have a starting point for defining what "good" looks like rather than starting from scratch.

### SUS5 Statistical significance surfacing
As a user, I want the product to surface the number of discordant pairs between models and flag when sample sizes are insufficient for statistical conclusions — so that I am not misled by differences that could be noise (e.g. 8/10 vs 6/10 pass rates with only 4 disagreements).
