import { create } from "zustand";
import { apiClient } from "@/lib/api";

export interface Provider {
  id: string;
  provider: string;
  api_key: string;
  base_url?: string | null;
  display_name?: string;
  strip_model_prefix?: boolean;
}

export interface McpServer {
  id: string;
  name: string;
  command: string;
  args: string[];
  env: Record<string, string>;
  enabled: boolean;
}

export interface Task {
  id: string;
  name: string;
  description?: string | null;
  tags: string[];
  default_config_set_id?: string | null;
  archived: boolean;
}

export interface ConfigSet {
  id: string;
  name: string;
  description?: string | null;
  tags: string[];
  slot_order: string[];
  archived: boolean;
}

export interface ConfigSlot {
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
  tool_choice?: string | Record<string, unknown> | null;
  mcp_server_ids?: string[] | null;
  modality: string;
  task_type: string;
  enabled: boolean;
}

export interface RunChain {
  id: string;
  name: string;
  root_run_id?: string | null;
  default_config_set_id?: string | null;
  archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface Run {
  id: string;
  name?: string | null;
  status: string;
  kind: string;
  config_set_id: string;
  config_version_ids: string[];
  task_id?: string | null;
  chain_id?: string | null;
  parent_run_ids: string[];
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  summary?: Record<string, unknown> | null;
}

export interface ContentBlock {
  type: string;
  text?: string;
  artifact_id?: string;
  url?: string;
  mime_type?: string;
  filename?: string;
  detail?: string;
}

export interface RunInput {
  id: string;
  run_id: string;
  input_index: number;
  role: string;
  content: ContentBlock[];
  created_at: string;
}

export interface RunOutput {
  id: string;
  run_id: string;
  config_version_id: string;
  slot_id: string;
  provider_model_id: string;
  response_index: number;
  status: string;
  content: ContentBlock[];
  text?: string | null;
  error?: { type?: string; message?: string } | null;
  usage: Record<string, number | null>;
  completed_at?: string | null;
}

export interface Annotation {
  id: string;
  target: Record<string, any>;
  rating?: string | null;
  severity?: string | null;
  judge: string;
  comment: string;
  created_at: string;
  updated_at: string;
}

export interface Artifact {
  id: string;
  run_id: string;
  output_id?: string | null;
  kind: string;
  modality: string;
  mime_type: string;
  filename: string;
  path: string;
  size_bytes?: number | null;
  sha256?: string | null;
  created_at: string;
  metadata: Record<string, unknown>;
}

export interface RunChainDetail {
  chain: RunChain;
  edges: any[];
  view_state: any;
  runs: Run[];
  inputs: Record<string, RunInput[]>;
  outputs: Record<string, RunOutput[]>;
  events: Record<string, any[]>;
  annotations: Record<string, Annotation[]>;
  artifacts: Record<string, Artifact[]>;
  config_sets: ConfigSet[];
  config_slots: Record<string, ConfigSlot[]>;
  config_versions: Record<string, any[]>;
}

interface TukeyState {
  tasks: Task[];
  configSets: ConfigSet[];
  configSlots: Record<string, ConfigSlot[]>;
  runChains: RunChain[];
  activeChainId: string | null;
  activeDetail: RunChainDetail | null;
  providers: Provider[];
  mcpServers: McpServer[];
  loading: boolean;
  setActiveChainId: (id: string | null) => void;
  loadWorkspace: () => Promise<void>;
  loadChainDetail: (id?: string | null) => Promise<void>;
  setProviders: (providers: Provider[]) => void;
  setMcpServers: (servers: McpServer[]) => void;
  resetActive: () => void;
}

export const useTukeyStore = create<TukeyState>((set, get) => ({
  tasks: [],
  configSets: [],
  configSlots: {},
  runChains: [],
  activeChainId: null,
  activeDetail: null,
  providers: [],
  mcpServers: [],
  loading: false,

  setActiveChainId: (id) => set({ activeChainId: id, activeDetail: null }),
  setProviders: (providers) => set({ providers }),
  setMcpServers: (servers) => set({ mcpServers: servers }),
  resetActive: () => set({ activeChainId: null, activeDetail: null }),

  loadWorkspace: async () => {
    set({ loading: true });
    const [tasks, configSets, runChains, providers, mcpServers] = await Promise.all([
      apiClient.listTasks(),
      apiClient.listConfigSets(),
      apiClient.listRunChains(),
      apiClient.listProviders(),
      apiClient.listMcpServers(),
    ]);
    const configSlots: Record<string, ConfigSlot[]> = {};
    await Promise.all(
      configSets.map(async (setItem: ConfigSet) => {
        configSlots[setItem.id] = await apiClient.listConfigSlots(setItem.id);
      }),
    );
    const visibleChains = runChains.filter((chain: RunChain) => !chain.archived);
    const activeChainId = get().activeChainId ?? visibleChains[0]?.id ?? null;
    set({
      tasks: tasks.filter((task: Task) => !task.archived),
      configSets: configSets.filter((item: ConfigSet) => !item.archived),
      configSlots,
      runChains: visibleChains,
      providers,
      mcpServers,
      activeChainId,
      loading: false,
    });
    if (activeChainId) {
      await get().loadChainDetail(activeChainId);
    }
  },

  loadChainDetail: async (id) => {
    const chainId = id ?? get().activeChainId;
    if (!chainId) {
      set({ activeDetail: null });
      return;
    }
    const detail = await apiClient.getRunChainDetail(chainId);
    set({ activeDetail: detail });
  },
}));

export function contentText(content: ContentBlock[] | undefined): string {
  return (content || [])
    .map((block) => {
      if (block.type === "text") return block.text || "";
      if (block.type === "image") return block.filename || block.artifact_id || "[image]";
      return `[${block.type}]`;
    })
    .filter(Boolean)
    .join("\n");
}
