# Data Structure Contracts

This document records Tukey's data contracts as implemented today, including the run-native config-set/run-chain redesign and the artifact-backed multimodal execution path.

## Architecture Decisions

- Runs are the only execution primitive. Exploratory comparisons, formal evals, agent-driven batches, scheduled monitoring, retries, and chat-like continuations all create `Run` and `RunOutput` records through the same run engine.
- Chatrooms are retired as product/data primitives. No migration support is required.
- Experiments are retired as execution/data primitives. The legacy experiment code describes the current implementation only; future formal evals are optional orchestration over runs.
- Eval plans are optional. They hold durable criteria, prompt/test sets, config-set references, and schedules when needed, but they must not introduce a separate execution path.
- Tasks/use cases are user-facing organization. They name what is being evaluated and can contain exploratory chains, eval plans, scheduled runs, and summaries.
- Agents and cron jobs use the same public contracts as the UI. They should not write storage files directly.

## Rationale

Exploratory comparison, formal evals, and agent-operated model monitoring share the same underlying data: configs, immutable config snapshots, inputs, outputs, annotations, metadata, and lineage. Keeping one run substrate avoids the current split between chatrooms and experiments while still supporting a slick exploratory-to-formal workflow. A user can start with a run chain, then promote selected prompts, outputs, criteria, and config sets into an eval plan without rewriting existing execution records.

## Present State

The active product surface is run-native:

- Config sets and frozen config versions define model/provider/task execution settings.
- Runs are the execution records for text and multimodal work.
- Run chains provide the chat-like comparison view and explicit lineage.
- Artifacts store generated or uploaded image bytes and are referenced from run inputs/outputs.

Legacy chatroom and experiment code still exists for compatibility and historical tests, but it is no longer the target product contract.

The legacy app had two partially separate domains:

- Interactive comparison: `chatrooms -> chats -> messages/responses`.
- Batch evaluation: `experiments -> runs -> results/annotations`.

Experiments currently depend on chatrooms for model configuration. The frontend mostly knows the interactive comparison domain; experiment runs exist through REST/backend code but do not have a first-class frontend UI.

### Storage Layout

Root data directory defaults to `~/.tukey`, or another configured data directory.

```text
<data_dir>/
  config.json
  chatrooms/
    <chatroom_id>/
      meta.json
      chats/
        <chat_id>/
          meta.json
          messages.jsonl
          annotations.jsonl
  experiments/
    <experiment_id>/
      meta.json
      test_cases.jsonl
      runs/
        <run_id>/
          meta.json
          results.jsonl
          annotations.jsonl
```

Global data-dir configuration lives outside the selected data directory:

```text
~/.tukey/tukey-global.json
```

### Global Config Contract

Stored in `<data_dir>/config.json`.

```ts
interface ConfigFile {
  providers: Provider[];
  mcp_servers: McpServer[];
}

interface Provider {
  id: string;
  provider: string;
  api_key: string;
  base_url?: string | null;
  display_name?: string;
  strip_model_prefix?: boolean;
}

interface McpServer {
  id: string;
  name: string;
  command: string;
  args: string[];
  env: Record<string, string>;
  enabled: boolean;
}
```

Notes:

- Provider records include secrets.
- Provider snapshots copied into chat/run metadata intentionally strip `api_key`.
- MCP server records are mutable global config.

### Model Config Contract

Model configs are currently embedded inside `chatroom.meta.models` and copied into `chat.meta.models_snapshot` and `run.meta.models_snapshot`.

```ts
interface ModelConfig {
  id: string;
  provider_id: string;
  model_id: string;
  display_name: string;
  system_prompt: string;
  temperature: number;
  max_tokens?: number | null;
  top_p?: number | null;
  extra_params: Record<string, unknown>;
  response_format?: {
    type: string;
    json_schema?: Record<string, unknown>;
  } | null;
  tools?: Record<string, unknown>[] | null;
  tool_choice?: string | {
    type: string;
    function: { name: string };
  } | null;
  mcp_server_ids?: string[] | null;
}
```

Important behavior:

- Model configs are mutable through chatroom updates.
- Chat creation snapshots chatroom models into `models_snapshot`.
- WebSocket send re-snapshots a chat from current chatroom models only for the first message if the chat has no messages.
- Experiment runs snapshot models from the linked chatroom at run start.
- There is no immutable config-version record today.

### Chatroom Contract

Stored in `chatrooms/<chatroom_id>/meta.json`.

```ts
interface ChatroomMeta {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  models: ModelConfig[];
}
```

REST:

- `GET /api/chat/chatrooms -> ChatroomMeta[]`
- `POST /api/chat/chatrooms { name, models? } -> ChatroomMeta`
- `GET /api/chat/chatrooms/{chatroom_id} -> ChatroomMeta`
- `PATCH /api/chat/chatrooms/{chatroom_id} { name?, models? } -> ChatroomMeta`
- `DELETE /api/chat/chatrooms/{chatroom_id} -> 204`

### Chat Contract

Stored in `chatrooms/<chatroom_id>/chats/<chat_id>/meta.json`.

```ts
interface ChatMeta {
  id: string;
  name: string;
  models_snapshot: ModelConfig[];
  providers_snapshot: Record<string, ProviderSnapshot>;
  runtime: RuntimeSnapshot;
  created_at: string;
}

interface ProviderSnapshot {
  id: string;
  provider?: string;
  base_url?: string | null;
  display_name?: string;
}

interface RuntimeSnapshot {
  tukey_version: string;
  httpx_version: string;
  python_version: string;
}
```

REST:

- `GET /api/chat/chatrooms/{chatroom_id}/chats -> ChatMeta[]`
- `POST /api/chat/chatrooms/{chatroom_id}/chats { name? } -> ChatMeta`
- `GET /api/chat/chatrooms/{chatroom_id}/chats/{chat_id} -> ChatMeta`
- `PATCH /api/chat/chatrooms/{chatroom_id}/chats/{chat_id} { name?, models_snapshot?, providers_snapshot? } -> ChatMeta`
- `DELETE /api/chat/chatrooms/{chatroom_id}/chats/{chat_id} -> 204`

### Chat Message And Response Contract

Stored in `messages.jsonl`. Each line is a user turn with model fan-out responses.

```ts
interface ChatMessage {
  id: string;
  role: "user";
  content: string;
  created_at: string;
  responses: ResponseMeta[];
  response_indices?: Record<string, number>;
}

interface ResponseMeta {
  model_id: string;        // currently ModelConfig.id, not provider model_id
  response_index: number;
  content: string;
  tokens_in?: number;
  tokens_out?: number;
  cost?: number | null;
  duration_ms?: number;
  tokens_per_sec?: number;
  error?: boolean;
  tool_interactions?: ToolInteraction[];
}

interface ToolInteraction {
  tool_calls: {
    id: string;
    name: string;
    arguments: string;
  }[];
  tool_results: {
    tool_call_id: string;
    name: string;
    result: string;
    error?: boolean;
  }[];
}
```

REST:

- `GET /api/chat/chatrooms/{chatroom_id}/chats/{chat_id}/messages -> ChatMessage[]`
- `POST /api/chat/chatrooms/{chatroom_id}/chats/{chat_id}/messages { content } -> ChatMessage`

WebSocket:

- URL: `/ws/chat/{chatroom_id}/{chat_id}`
- Client send:

```ts
type WsClientSend =
  | {
      type?: "send";
      content: string;
      n?: number; // clamped 1..9
      response_indices?: Record<string, number>;
    }
  | {
      type: "regenerate";
      turn_id: string;
      n?: number; // clamped 1..9
    };
```

- Server events:

```ts
type WsServerEvent =
  | { type: "turn_start"; turn_id: string; content: string }
  | {
      type: "chunk";
      turn_id: string;
      model_id: string;
      response_index: number;
      delta: string;
      done: boolean;
      metadata?: Partial<ResponseMeta>;
    }
  | {
      type: "tool_call";
      turn_id: string;
      model_id: string;
      response_index: number;
      tool_call: { id: string; name: string; arguments: string };
    }
  | {
      type: "tool_result";
      turn_id: string;
      model_id: string;
      response_index: number;
      tool_result: {
        tool_call_id: string;
        name: string;
        result: string;
        error?: boolean;
      };
    }
  | {
      type: "error";
      turn_id: string;
      model_id: string;
      response_index: number;
      error: string;
    }
  | { type: "turn_complete"; turn_id: string; turn: ChatMessage }
  | { type: "turn_updated"; turn_id: string; turn: ChatMessage };
```

Important behavior:

- WebSocket send writes a skeleton `ChatMessage` before streaming responses.
- `turn_complete` replaces the skeleton with completed responses.
- Regeneration appends new `ResponseMeta` entries to the existing turn.
- `response_indices` is currently turn-level in frontend behavior, not truly per model/response lineage.

### Chat Annotation Contract

Stored in `annotations.jsonl` under a chat.

```ts
interface ChatAnnotation {
  id: string;
  target: {
    source: {
      message_id: string;
      model_id: string;
      response_index: number;
    };
    selector: {
      type: "TextQuoteSelector";
      exact: string;
      prefix: string;
      suffix: string;
    };
  };
  rating: "positive" | "negative";
  comment: string;
  created: string;
  modified: string;
}
```

REST:

- `POST /api/chat/chatrooms/{chatroom_id}/chats/{chat_id}/annotations -> ChatAnnotation`
- `GET /api/chat/chatrooms/{chatroom_id}/chats/{chat_id}/annotations -> ChatAnnotation[]`
- `PATCH /api/chat/chatrooms/{chatroom_id}/chats/{chat_id}/annotations/{annotation_id} -> ChatAnnotation`
- `DELETE /api/chat/chatrooms/{chatroom_id}/chats/{chat_id}/annotations/{annotation_id} -> 204`

### Chat Manifest And Export Contract

Manifest:

```ts
interface ChatManifest {
  chatroom: {
    name: string;
    models: ModelConfig[];
  };
  chat: {
    id: string;
    name?: string;
    created_at?: string;
    models_snapshot: ModelConfig[];
    providers_snapshot: Record<string, ProviderSnapshot>;
    runtime: RuntimeSnapshot;
  };
  turns: {
    content: string;
    responses: {
      model_id: string;
      tokens_in?: number;
      tokens_out?: number;
      cost?: number | null;
      duration_ms?: number;
      error: boolean;
    }[];
  }[];
}
```

REST:

- `GET /api/chat/chatrooms/{chatroom_id}/chats/{chat_id}/manifest -> ChatManifest`
- `POST /api/chat/chatrooms/{chatroom_id}/chats/{chat_id}/replay -> { chat, turns }`
- `POST /api/chat/chatrooms/{chatroom_id}/export`
- `POST /api/chat/chatrooms/{chatroom_id}/chats/{chat_id}/export`
- `POST /api/chat/chatrooms/import`

Export/import remaps chatroom, chat, message, and annotation IDs during import.

### Experiment Contract

Stored in `experiments/<experiment_id>/meta.json`.

```ts
interface ExperimentMeta {
  id: string;
  name: string;
  version: number;
  status: "draft" | "running" | "complete";
  chatroom_id: string;
  brief: Record<string, unknown>; // must include decision
  created_at: string;
  updated_at: string;
}
```

REST:

- `POST /api/experiments { name, chatroom_id, brief } -> ExperimentMeta`
- `GET /api/experiments -> ExperimentMeta[]`
- `GET /api/experiments/{experiment_id} -> ExperimentMeta`
- `PATCH /api/experiments/{experiment_id} { name?, brief? } -> ExperimentMeta`
- `DELETE /api/experiments/{experiment_id} -> 204`

### Test Case Contract

Stored in `experiments/<experiment_id>/test_cases.jsonl`.

```ts
interface TestCase {
  id: string;
  turns: Array<string | { role?: string; content: string }>;
  expected_output?: unknown;
  tags: string[];
  overrides: Partial<ModelConfig>;
}
```

REST:

- `POST /api/experiments/{experiment_id}/test-cases { test_cases } -> TestCase[]`
- `GET /api/experiments/{experiment_id}/test-cases -> TestCase[]`
- `PUT /api/experiments/{experiment_id}/test-cases { test_cases } -> TestCase[]`

### Experiment Run Contract

Stored in `experiments/<experiment_id>/runs/<run_id>/meta.json`.

```ts
interface ExperimentRunMeta {
  id: string;
  experiment_id: string;
  version: number;
  status: "running" | "complete";
  models_snapshot: ModelConfig[];
  providers_snapshot: Record<string, ProviderSnapshot>;
  runtime: RuntimeSnapshot;
  created_at: string;
  completed_at?: string;
}
```

REST:

- `POST /api/experiments/{experiment_id}/run -> ExperimentRunMeta`
- `GET /api/experiments/{experiment_id}/runs -> ExperimentRunMeta[]`
- `GET /api/experiments/{experiment_id}/runs/{run_id} -> ExperimentRunMeta`

### Experiment Result Contract

Stored in `experiments/<experiment_id>/runs/<run_id>/results.jsonl`.

```ts
interface ExperimentResult {
  id: string;
  run_id: string;
  test_case_id: string;
  model_id: string; // ModelConfig.id
  exchanges: {
    input: string;
    output: string;
    tokens_in: number;
    tokens_out: number;
    cost: number;
    duration_ms: number;
  }[];
  total_tokens_in: number;
  total_tokens_out: number;
  total_cost: number;
  total_duration_ms: number;
  error: boolean;
}
```

REST:

- `GET /api/experiments/{experiment_id}/runs/{run_id}/results -> ExperimentResult[]`

### Experiment Annotation And Summary Contract

Stored in `experiments/<experiment_id>/runs/<run_id>/annotations.jsonl`.

```ts
interface ExperimentAnnotation {
  id: string;
  result_id: string;
  judge: string;
  verdict: "pass" | "fail" | "partial";
  severity?: string | null;
  notes?: string | null;
  criteria_id?: string | null;
  created_at: string;
}

interface ExperimentRunSummary {
  run_id: string;
  total_results: number;
  total_annotations: number;
  per_model: {
    model_id: string;
    total: number;
    pass: number;
    fail: number;
    partial: number;
    unannotated: number;
    errors: number;
    total_cost: number;
    total_duration_ms: number;
  }[];
}
```

REST:

- `POST /api/experiments/{experiment_id}/runs/{run_id}/annotations -> ExperimentAnnotation`
- `GET /api/experiments/{experiment_id}/runs/{run_id}/annotations -> ExperimentAnnotation[]`
- `GET /api/experiments/{experiment_id}/runs/{run_id}/summary -> ExperimentRunSummary`

### Provider Runtime Contract

Provider implementations satisfy:

```ts
interface LLMResponse {
  content: string;
  tokens_in: number;
  tokens_out: number;
  cost: number | null;
  duration_ms: number;
  tokens_per_sec: number;
  model: string;
  raw_response: Record<string, unknown>;
}

interface ImageResult {
  data: Uint8Array;
  mime_type: string;
  revised_prompt?: string | null;
  metadata: Record<string, unknown>;
}

interface ImageResponse {
  images: ImageResult[];
  content: string;
  usage: Record<string, unknown>;
  cost: number | null;
  duration_ms: number;
  model: string;
  raw_response: Record<string, unknown>;
}

interface StreamChunk {
  delta: string;
  done: boolean;
  response?: LLMResponse | null;
  tool_calls?: { id: string; name: string; arguments: string }[] | null;
  tool_result?: {
    tool_call_id: string;
    name: string;
    result: string;
    error: boolean;
  } | null;
}
```

### Synthesis Contract

Legacy synthesis tools receive an `ExperimentBundle`, not storage directly.

```ts
interface ExperimentBundle {
  experiment_id: string;
  experiment_name: string;
  run_id: string;
  brief: Record<string, unknown>;
  test_cases: TestCase[];
  models: ModelSnapshot[];
  results_by_model: Record<string, Result[]>;
  results: Result[];
}

interface ModelSnapshot {
  id: string;
  model_id: string;
  display_name: string;
  system_prompt?: string | null;
  temperature?: number | null;
  max_tokens?: number | null;
  provider_id?: string | null;
}
```

Adapters currently build bundles from either chatrooms or experiment runs.

### Frontend Store Contract

`ui/src/stores/chatStore.ts` mirrors the interactive domain:

- `Provider[]`
- `McpServer[]`
- `Chatroom[]`
- `Chat[]`
- `Message[]`
- streaming entries keyed by `${modelId}:${responseIndex}`

The active frontend store uses run-native tasks, config sets, run chains, runs, outputs, annotations, and artifacts. Legacy chat store contracts are retained only for legacy routes/tests.

### Present-State Contract Issues

- Chatrooms own mutable model configs, so configs are not first-class or reusable outside chatrooms.
- `model_id` often means `ModelConfig.id`, not provider model ID, which is ambiguous.
- Interactive messages and experiment results use different shapes for similar concepts.
- Experiment runs are nested under experiments, while interactive turns are nested under chats.
- Annotations have separate chat and experiment schemas.
- Tool interactions are recorded for chat responses but not experiment results.
- WebSocket events are chat-specific.
- Artifact-backed image inputs and outputs are now supported by the run-native backend.
- Provider and MCP configs are mutable; snapshots strip secrets but are not versioned as first-class records.
- Synthesis adapts multiple legacy shapes into one bundle rather than reading a single run-native contract.

## Future State

The target model replaces chatrooms and experiments with:

- Tasks/use cases: optional user-facing containers for what is being evaluated.
- Config sets: editable collections of config slots.
- Config versions: immutable snapshots of config slots once used.
- Runs: execution records for interactive, eval, scheduled, and agent-driven work.
- Run chains: explicit lineage between runs that can look like chats in the UI.
- Eval plans: optional formal-eval orchestration over tasks, test cases, config sets, and schedules.
- Schedules: optional cron/agent automation over tasks, eval plans, config sets, and provider model discovery.
- Views: frontend projections over runs and chains.

No migration from chatrooms or legacy experiments is required.

### Future Storage Layout

Proposed layout:

```text
<data_dir>/
  config.json
  providers/
    provider_versions.jsonl
  tasks/
    <task_id>/
      meta.json
  config_sets/
    <config_set_id>/
      meta.json
      slots.json
      versions.jsonl
  eval_plans/
    <eval_plan_id>/
      meta.json
      test_cases.jsonl
  schedules/
    <schedule_id>/
      meta.json
  runs/
    <run_id>/
      meta.json
      inputs.jsonl
      outputs.jsonl
      events.jsonl
      annotations.jsonl
      artifacts/
        <artifact_id>.<ext>
  run_chains/
    <chain_id>/
      meta.json
      edges.jsonl
      view_state.json
```

Decision: start with this directory layout for local-first inspectability. Add derived indexes later for search/performance rather than starting with a second global-log source of truth.

### Future Shared Types

Use explicit IDs to avoid current ambiguity:

- `slot_id`: active editable slot in a config set.
- `config_version_id`: immutable used config snapshot.
- `provider_model_id`: model ID sent to the provider.
- `output_id`: one concrete model response/artifact.
- `run_id`: one execution record.
- `chain_id`: one conversational or branching lineage view.
- `task_id`: optional user-facing task/use-case container.
- `eval_plan_id`: optional formal-eval orchestration container.
- `schedule_id`: optional cron/agent automation container.

### Config Set Contract

```ts
interface ConfigSet {
  id: string;
  name: string;
  description?: string;
  tags: string[];
  slot_order: string[];
  archived: boolean;
  created_at: string;
  updated_at: string;
}

interface ConfigSlot {
  id: string;
  config_set_id: string;
  name: string;
  provider_id: string;
  provider_model_id: string;
  display_name: string;
  system_prompt: string;
  temperature?: number | null;
  max_tokens?: number | null;
  top_p?: number | null;
  extra_params: Record<string, unknown>;
  response_format?: Record<string, unknown> | null;
  tools?: Record<string, unknown>[] | null;
  tool_choice?: unknown | null;
  mcp_server_ids?: string[] | null;
  modality?: "text" | "image" | "audio" | "video" | "multimodal";
  task_type?: "chat_completion" | "image_generation" | "image_edit" | "embedding" | string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}
```

Contract rules:

- Config sets and slots are mutable until used.
- Removing a slot from a config set only removes it from active selection; it does not delete any config version.
- Slot order is presentation state, not run lineage.

### Config Version Contract

```ts
interface ConfigVersion {
  id: string;
  config_set_id: string;
  slot_id: string;
  version: number;
  content_hash: string;
  created_at: string;
  created_by?: "user" | "agent" | "system";
  first_used_run_id?: string;
  slot_snapshot: ConfigSlot;
  provider_snapshot: ProviderSnapshot;
  mcp_server_snapshots: McpServerSnapshot[];
  runtime?: RuntimeSnapshot;
}
```

Contract rules:

- A config version is immutable once created.
- A run references config versions, not active config slots.
- If a slot's current content matches an existing version hash, reuse the existing version instead of writing a duplicate.
- Provider snapshots must not include `api_key`.

### Run Contract

```ts
interface Run {
  id: string;
  name?: string;
  status: "queued" | "running" | "complete" | "failed" | "cancelled";
  kind: "interactive" | "eval" | "agent" | "scheduled" | "preflight";
  config_set_id: string;
  config_version_ids: string[];
  task_id?: string | null;
  eval_plan_id?: string | null;
  schedule_id?: string | null;
  chain_id?: string | null;
  parent_run_ids: string[];
  created_at: string;
  started_at?: string;
  completed_at?: string;
  created_by?: "user" | "agent" | "system";
  runtime: RuntimeSnapshot;
  summary?: RunSummary;
}
```

`Run` is the common parent for one-shot prompts, batch test cases, chat-like turns, retries, scheduled checks, and agent-driven evaluations.

### Run Input Contract

```ts
interface RunInput {
  id: string;
  run_id: string;
  input_index: number;
  role?: "user" | "system" | "developer" | "tool";
  content: ContentBlock[];
  test_case_id?: string | null;
  source?: {
    type: "user" | "test_case" | "agent" | "prior_output";
    ref_id?: string;
  };
  created_at: string;
}

type ContentBlock =
  | { type: "text"; text: string }
  | { type: "image"; url: string; mime_type?: string; detail?: string }
  | { type: "artifact"; artifact_id: string; mime_type?: string; detail?: string }
  | { type: "file"; artifact_id: string; mime_type: string; filename?: string }
  | { type: "json"; value: unknown };
```

Contract rules:

- Text-only runs use a single `{ type: "text" }` block.
- Multimodal runs use content blocks and artifact references.
- `image.url` is expected to be provider-compatible, normally a base64 data URL in v1.
- `artifact` image blocks resolve to data URLs at provider-call time.
- Raw artifacts live under the run's `artifacts/` directory.

### Run Output Contract

```ts
interface RunOutput {
  id: string;
  run_id: string;
  config_version_id: string;
  slot_id: string;
  provider_model_id: string;
  response_index: number;
  status: "running" | "complete" | "failed" | "cancelled";
  content: ContentBlock[];
  text?: string; // convenience projection only; content is canonical
  error?: {
    message: string;
    type?: string;
    retryable?: boolean;
  };
  usage: {
    input_tokens?: number;
    output_tokens?: number;
    total_tokens?: number;
    cost?: number | null;
    duration_ms?: number;
    tokens_per_sec?: number;
  };
  raw_response_ref?: string;
  tool_interactions?: ToolInteraction[];
  created_at: string;
  completed_at?: string;
}
```

Contract rules:

- `response_index` is scoped to `(run_id, config_version_id)`.
- Retry/additional responses create new `RunOutput` rows, not a replacement.
- The first successful output can be marked in view state, not by deleting failed outputs.
- Errors are outputs with `status: "failed"`, preserving traceability.
- `content` is the canonical output body for every modality.
- `text` is a convenience projection for text-like outputs only and must not be used as the canonical result payload.

### Run Chain Contract

```ts
interface RunChain {
  id: string;
  name: string;
  root_run_id?: string | null;
  created_at: string;
  updated_at: string;
  archived: boolean;
  default_config_set_id?: string | null;
}

interface RunEdge {
  id: string;
  chain_id: string;
  parent_run_id: string;
  child_run_id: string;
  mapping: {
    // key can be slot_id or config_version_id
    [slotOrVersionId: string]: {
      output_id: string;
      response_index: number;
    };
  };
  created_at: string;
}

interface RunChainViewState {
  chain_id: string;
  selected_outputs: Record<string, string>; // slot_id/config_version_id -> output_id
  pinned_output_ids: string[];
  collapsed_run_ids: string[];
  visible_slot_ids?: string[];
  comparison_order?: string[];
}
```

Contract rules:

- A chain is a view plus lineage, not the execution object itself.
- Follow-up context is explicit through `RunEdge.mapping`.
- Different slots can continue from different prior outputs.
- Branching is allowed because a run can have multiple child runs.

### Annotation Contract

Unify legacy chat and legacy experiment annotations:

```ts
interface Annotation {
  id: string;
  target: {
    type: "run" | "output" | "artifact" | "text_range";
    run_id?: string;
    output_id?: string;
    artifact_id?: string;
    selector?: {
      type: "TextQuoteSelector" | "ImageRegionSelector" | "JsonPointerSelector";
      exact?: string;
      prefix?: string;
      suffix?: string;
      x?: number;
      y?: number;
      width?: number;
      height?: number;
      pointer?: string;
    };
  };
  rating?: "positive" | "negative" | "pass" | "fail" | "partial";
  severity?: "minor" | "major" | "critical" | string | null;
  criteria_id?: string | null;
  judge: "human" | "agent" | string;
  comment: string;
  created_at: string;
  updated_at: string;
}
```

### Task, Eval Plan, And Schedule Contracts

Tasks/use cases are optional user-facing containers. Eval plans are optional formal-eval orchestration. Schedules are optional automation over tasks, eval plans, or config sets. None of these objects execute model calls directly; they create or group runs.

```ts
interface Task {
  id: string;
  name: string;
  description?: string;
  tags: string[];
  default_config_set_id?: string | null;
  created_at: string;
  updated_at: string;
  archived: boolean;
}

interface EvalPlan {
  id: string;
  task_id?: string | null;
  name: string;
  version: number;
  status: "draft" | "active" | "archived";
  brief: {
    decision: string;
    criteria?: unknown[];
    judges?: string[];
  };
  config_set_ids: string[];
  prompt_set_ids?: string[];
  created_at: string;
  updated_at: string;
}

interface EvalTestCase {
  id: string;
  eval_plan_id: string;
  turns: RunInput[];
  expected_output?: unknown;
  tags: string[];
  overrides?: Partial<ConfigSlot>;
}

interface Schedule {
  id: string;
  task_id?: string | null;
  eval_plan_id?: string | null;
  config_set_id?: string | null;
  name: string;
  status: "active" | "paused";
  cadence: {
    type: "cron" | "interval" | "manual";
    expression?: string;
    timezone?: string;
  };
  model_discovery?: {
    provider_ids: string[];
    include_patterns?: string[];
    exclude_patterns?: string[];
    require_user_approval?: boolean;
  };
  created_at: string;
  updated_at: string;
  last_run_id?: string | null;
}
```

Eval plans and schedules create `Run` records. A plan is not required for an exploratory run chain.

### Artifact Contract

Needed for multimodal support.

```ts
interface Artifact {
  id: string;
  run_id?: string;
  output_id?: string;
  kind: "input" | "output" | "intermediate";
  modality: "image" | "audio" | "video" | "file" | "json";
  mime_type: string;
  filename: string;
  path: string;
  size_bytes?: number;
  sha256?: string;
  created_at: string;
  metadata?: Record<string, unknown>;
}
```

Artifact rules:

- `Storage.write_artifact_bytes()` writes bytes under `runs/{run_id}/artifacts/`, computes `sha256`, stores size and mime type, and appends artifact metadata.
- `Storage.read_artifact_bytes()` resolves metadata back to bytes with path-escape protection.
- Generated and edited images are stored as `kind: "output"`, `modality: "image"` artifacts and referenced from `RunOutput.content`.
- Input images can be represented as existing `artifact` content blocks and are converted to base64 data URLs for provider calls.

### Future REST API Surface

Tasks:

- `GET /api/tasks`
- `POST /api/tasks`
- `GET /api/tasks/{task_id}`
- `PATCH /api/tasks/{task_id}`
- `DELETE /api/tasks/{task_id}` or archive

Config sets:

- `GET /api/config-sets`
- `POST /api/config-sets`
- `GET /api/config-sets/{config_set_id}`
- `PATCH /api/config-sets/{config_set_id}`
- `DELETE /api/config-sets/{config_set_id}` or archive
- `GET /api/config-sets/{config_set_id}/slots`
- `POST /api/config-sets/{config_set_id}/slots`
- `PATCH /api/config-sets/{config_set_id}/slots/{slot_id}`
- `DELETE /api/config-sets/{config_set_id}/slots/{slot_id}` or disable
- `GET /api/config-sets/{config_set_id}/versions`

Runs:

- `POST /api/runs`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/inputs`
- `GET /api/runs/{run_id}/outputs`
- `POST /api/runs/{run_id}/retry`
- `POST /api/runs/{run_id}/cancel`
- `GET /api/runs/{run_id}/events`
- `GET /api/runs/{run_id}/summary`

Run chains:

- `GET /api/run-chains`
- `POST /api/run-chains`
- `GET /api/run-chains/{chain_id}`
- `PATCH /api/run-chains/{chain_id}`
- `POST /api/run-chains/{chain_id}/runs`
- `GET /api/run-chains/{chain_id}/edges`
- `PUT /api/run-chains/{chain_id}/view-state`

Eval plans:

- `GET /api/eval-plans`
- `POST /api/eval-plans`
- `GET /api/eval-plans/{eval_plan_id}`
- `PATCH /api/eval-plans/{eval_plan_id}`
- `POST /api/eval-plans/{eval_plan_id}/test-cases`
- `GET /api/eval-plans/{eval_plan_id}/test-cases`
- `PUT /api/eval-plans/{eval_plan_id}/test-cases`
- `POST /api/eval-plans/{eval_plan_id}/runs`

Schedules:

- `GET /api/schedules`
- `POST /api/schedules`
- `GET /api/schedules/{schedule_id}`
- `PATCH /api/schedules/{schedule_id}`
- `DELETE /api/schedules/{schedule_id}`
- `POST /api/schedules/{schedule_id}/run-now`

Annotations:

- `GET /api/annotations?run_id=...&output_id=...`
- `POST /api/annotations`
- `PATCH /api/annotations/{annotation_id}`
- `DELETE /api/annotations/{annotation_id}`

Artifacts:

- `GET /api/artifacts/{artifact_id}`
- `GET /api/artifacts/{artifact_id}/content`
- `POST /api/artifacts`
- `GET /api/runs/{run_id}/artifacts`

### Future WebSocket Contract

Replace chat-specific WebSocket paths with run-specific execution events.

```text
/ws/runs/{run_id}
/ws/run-chains/{chain_id}
```

Server events:

```ts
type RunEvent =
  | { type: "run_started"; run: Run }
  | { type: "input_recorded"; input: RunInput }
  | {
      type: "output_delta";
      run_id: string;
      output_id: string;
      config_version_id: string;
      response_index: number;
      delta?: ContentBlock;
    }
  | { type: "tool_call"; output_id: string; tool_call: ToolInteraction["tool_calls"][number] }
  | { type: "tool_result"; output_id: string; tool_result: ToolInteraction["tool_results"][number] }
  | { type: "output_completed"; output: RunOutput }
  | { type: "output_failed"; output: RunOutput }
  | { type: "run_completed"; run: Run }
  | { type: "run_failed"; run: Run; error: string }
  | { type: "chain_edge_added"; edge: RunEdge };
```

Client commands:

```ts
type RunCommand =
  | {
      type: "start_run";
      config_set_id: string;
      inputs: ContentBlock[];
      n?: number;
      chain_id?: string;
      task_id?: string;
      eval_plan_id?: string;
      schedule_id?: string;
      parent_mapping?: RunEdge["mapping"];
    }
  | {
      type: "retry_outputs";
      output_ids?: string[];
      config_version_ids?: string[];
      n?: number;
    }
  | { type: "cancel_run"; run_id: string };
```

### Future Frontend Store Shape

```ts
interface TukeyState {
  providers: Provider[];
  mcpServers: McpServer[];
  tasks: Task[];
  activeTaskId: string | null;
  configSets: ConfigSet[];
  activeConfigSetId: string | null;
  configSlotsBySet: Record<string, ConfigSlot[]>;
  configVersionsBySet: Record<string, ConfigVersion[]>;
  evalPlans: EvalPlan[];
  schedules: Schedule[];
  runChains: RunChain[];
  activeRunChainId: string | null;
  runsById: Record<string, Run>;
  runInputsByRun: Record<string, RunInput[]>;
  runOutputsByRun: Record<string, RunOutput[]>;
  annotationsByTarget: Record<string, Annotation[]>;
  artifactsById: Record<string, Artifact>;
  streamingOutputs: Record<string, Partial<RunOutput>>;
}
```

The frontend should derive conversation and comparison views from runs, outputs, and chain view state, not from a separate chat message model.

### Component Change Plan

Storage:

- Add task, config-set, config-version, run, run-chain, eval-plan, schedule, annotation, and artifact helpers.
- Keep JSON/JSONL implementation initially for local-first inspectability.
- Make config-version writes append-only.
- Store raw provider responses or references for traceability.

Backend execution:

- Use a multimodal `RunEngine` that accepts config versions plus content-block inputs and emits run events.
- `RunEngine` dispatches by `ConfigSlot.task_type` from the frozen config version, including `chat_completion`, `image_generation`, `image_edit`, and future task types.
- The current executors implement `chat_completion`, `image_generation`, and `image_edit`; unsupported future task types create failed outputs.
- Existing text-shaped provider responses are adapted into run-native execution results before persistence; provider protocols are not the engine contract.
- Image outputs are persisted as artifacts and referenced from `RunOutput.content`.
- Unsupported task types create failed `RunOutput` records with structured errors rather than crashing or creating a second execution path.
- Make interactive, eval, scheduled, and agent execution all call `RunEngine`.
- Move current chat `send_message` and legacy experiment `_execute_pair` logic behind the shared run contract.
- Add queue/progress/cancel hooks before expanding automated batches.

REST routes:

- Add new `/api/tasks`, `/api/config-sets`, `/api/runs`, `/api/run-chains`, `/api/eval-plans`, `/api/schedules`, `/api/annotations`, and `/api/artifacts` routes.
- Keep old chat and experiment routes only while code is transitioning if needed, but do not treat them as target contracts.

WebSocket:

- Replace `/ws/chat/{chatroom_id}/{chat_id}` with run/chain streaming.
- Use `output_id` as the streaming key instead of `${modelId}:${responseIndex}`.
- Support reconnect/resume by replaying `events.jsonl` and current output state.

Frontend:

- Replace chatroom sidebar with tasks, config sets, and run chains.
- Replace message state with run chain projection.
- Response cards bind to `RunOutput`.
- Config UI edits `ConfigSlot`; execution freezes `ConfigVersion`.
- Progressive disclosure shows lineage/DAG only when needed.

Synthesis:

- Replace `ExperimentBundle` naming with `RunBundle`, or keep the class temporarily while changing its source to runs/run chains.
- Build analysis bundles from `Run`, `RunOutput`, `Annotation`, `ConfigVersion`, `Task`, and optional `EvalPlan`.

Search:

- Index config set names, slot names, provider model IDs, prompts, output text, annotation comments, tags, and artifact metadata.

Codex skill/plugin:

- Contract should expose a small safe workflow: discover health, list/create provider, create task/config set, run prompt/test case, inspect outputs, summarize.
- Prefer high-level endpoints over making agents manually compose storage paths.

### Incremental Implementation Sequence

1. Add future data types and storage helpers without wiring UI.
2. Add task/config-set CRUD and config-version freezing.
3. Add run CRUD and a multimodal-ready `RunEngine` with an initial chat/text executor.
4. Adapt interactive send to create `Run` and `RunOutput` records.
5. Add run-chain creation and continuation mapping.
6. Add optional eval plans backed by runs; port legacy experiment behavior onto this path.
7. Add schedules for cron/agent model monitoring.
8. Unify annotations around run/output targets.
9. Move synthesis to run-native bundles.
10. Extend artifact-backed multimodal executors for image generation/editing and richer content blocks.
11. Replace frontend chatroom surfaces with task/config-set/run-chain views.

### Non-Goals For The Redesign

- No chatroom migration.
- No legacy experiment migration.
- No cloud sync.
- No multi-user collaboration unless added later.
- No mandatory visible graph editor for basic use.
- No single winner score baked into the core contract.
- No second execution engine for formal evals.
