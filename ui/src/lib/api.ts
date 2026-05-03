const BASE = "";

async function api<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const apiClient = {
  listTasks: () => api<any[]>("/api/tasks"),
  createTask: (data: any) =>
    api<any>("/api/tasks", { method: "POST", body: JSON.stringify(data) }),
  updateTask: (id: string, data: any) =>
    api<any>(`/api/tasks/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteTask: (id: string) => api<void>(`/api/tasks/${id}`, { method: "DELETE" }),

  listConfigSets: () => api<any[]>("/api/config-sets"),
  createConfigSet: (data: any) =>
    api<any>("/api/config-sets", { method: "POST", body: JSON.stringify(data) }),
  getConfigSet: (id: string) => api<any>(`/api/config-sets/${id}`),
  updateConfigSet: (id: string, data: any) =>
    api<any>(`/api/config-sets/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteConfigSet: (id: string) =>
    api<void>(`/api/config-sets/${id}`, { method: "DELETE" }),
  listConfigSlots: (configSetId: string) =>
    api<any[]>(`/api/config-sets/${configSetId}/slots`),
  createConfigSlot: (configSetId: string, data: any) =>
    api<any>(`/api/config-sets/${configSetId}/slots`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateConfigSlot: (configSetId: string, slotId: string, data: any) =>
    api<any>(`/api/config-sets/${configSetId}/slots/${slotId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteConfigSlot: (configSetId: string, slotId: string) =>
    api<void>(`/api/config-sets/${configSetId}/slots/${slotId}`, { method: "DELETE" }),
  listConfigVersions: (configSetId: string) =>
    api<any[]>(`/api/config-sets/${configSetId}/versions`),

  listRunChains: () => api<any[]>("/api/run-chains"),
  createRunChain: (data: any) =>
    api<any>("/api/run-chains", { method: "POST", body: JSON.stringify(data) }),
  updateRunChain: (id: string, data: any) =>
    api<any>(`/api/run-chains/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  getRunChainDetail: (id: string) => api<any>(`/api/run-chains/${id}/detail`),
  exportRunChain: (id: string) =>
    api<any>(`/api/run-chains/${id}/export`, { method: "POST" }),
  updateRunChainViewState: (id: string, data: any) =>
    api<any>(`/api/run-chains/${id}/view-state`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  createRunChainEdge: (id: string, data: any) =>
    api<any>(`/api/run-chains/${id}/edges`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listRuns: () => api<any[]>("/api/runs"),
  createRun: (data: any) =>
    api<any>("/api/runs", { method: "POST", body: JSON.stringify(data) }),
  executeRun: (id: string, data: any) =>
    api<any>(`/api/runs/${id}/execute`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getRunOutputs: (id: string) => api<any[]>(`/api/runs/${id}/outputs`),
  artifactContentUrl: (artifactId: string) =>
    `/api/artifacts/${encodeURIComponent(artifactId)}/content`,

  listRunAnnotations: (params: { run_id?: string; output_id?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.run_id) query.set("run_id", params.run_id);
    if (params.output_id) query.set("output_id", params.output_id);
    return api<any[]>(`/api/annotations${query.toString() ? `?${query}` : ""}`);
  },
  createRunAnnotation: (data: any) =>
    api<any>("/api/annotations", { method: "POST", body: JSON.stringify(data) }),
  updateRunAnnotation: (id: string, data: any) =>
    api<any>(`/api/annotations/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteRunAnnotation: (id: string) =>
    api<void>(`/api/annotations/${id}`, { method: "DELETE" }),

  search: (q: string, limit = 50) =>
    api<{ results: any[] }>(`/api/search?q=${encodeURIComponent(q)}&limit=${limit}`),

  listProviders: () => api<any[]>("/api/config/providers"),
  createProvider: (data: any) =>
    api<any>("/api/config/providers", { method: "POST", body: JSON.stringify(data) }),
  updateProvider: (id: string, data: Record<string, any>) =>
    api<any>(`/api/config/providers/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteProvider: (id: string) =>
    api<void>(`/api/config/providers/${id}`, { method: "DELETE" }),
  testProvider: (id: string) =>
    api<{ ok: boolean; error?: string }>(`/api/config/providers/${id}/test`, {
      method: "POST",
    }),
  getModelCapabilities: (modelId: string) =>
    api<{
      supports_reasoning: boolean;
      supports_vision: boolean;
      max_tokens: number | null;
      max_input_tokens: number | null;
    }>(`/api/models/${encodeURIComponent(modelId)}/capabilities`),
  getAvailableModels: (providerId: string) =>
    api<{ id: string; name: string }[]>(`/api/models/providers/${providerId}/available`),

  quickSetup: (data: {
    api_key: string;
    provider?: string;
    base_url?: string | null;
    display_name?: string | null;
    models?: { model_id: string; display_name?: string }[];
    chatroom_name?: string;
    task_name?: string;
    config_set_name?: string;
    chain_name?: string;
  }) =>
    api<{ provider: any; config_set: any; slots: any[]; task: any; chain: any }>(
      "/api/config/quick-setup",
      { method: "POST", body: JSON.stringify(data) },
    ),

  listMcpServers: () => api<any[]>("/api/config/mcp-servers"),
  createMcpServer: (data: {
    name: string;
    command: string;
    args?: string[];
    env?: Record<string, string>;
  }) =>
    api<any>("/api/config/mcp-servers", { method: "POST", body: JSON.stringify(data) }),
  updateMcpServer: (id: string, data: any) =>
    api<any>(`/api/config/mcp-servers/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteMcpServer: (id: string) =>
    api<void>(`/api/config/mcp-servers/${id}`, { method: "DELETE" }),
  testMcpServer: (id: string) =>
    api<{ ok: boolean; error?: string; tools: { name: string; description: string }[] }>(
      `/api/config/mcp-servers/${id}/test`,
      { method: "POST" },
    ),

  getHealth: () => api<{ status: string; data_dir: string }>("/api/health"),
  browseDir: (currentDir?: string) =>
    api<{ selected: string | null }>("/api/config/browse-dir", {
      method: "POST",
      body: JSON.stringify(currentDir ? { data_dir: currentDir } : {}),
    }),
  setDataDir: (data_dir: string) =>
    api<{ status: string; data_dir: string }>("/api/config/data-dir", {
      method: "POST",
      body: JSON.stringify({ data_dir }),
    }),

  // Legacy chat API retained so older unused components still type-check.
  listChatrooms: () => api<any[]>("/api/chat/chatrooms"),
  createChatroom: (name: string, models: any[] = []) =>
    api<any>("/api/chat/chatrooms", { method: "POST", body: JSON.stringify({ name, models }) }),
  getChatroom: (id: string) => api<any>(`/api/chat/chatrooms/${id}`),
  updateChatroom: (id: string, data: any) =>
    api<any>(`/api/chat/chatrooms/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteChatroom: (id: string) =>
    api<void>(`/api/chat/chatrooms/${id}`, { method: "DELETE" }),
  listChats: (chatroomId: string) =>
    api<any[]>(`/api/chat/chatrooms/${chatroomId}/chats`),
  createChat: (chatroomId: string, name?: string) =>
    api<any>(`/api/chat/chatrooms/${chatroomId}/chats`, {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  getChat: (chatroomId: string, chatId: string) =>
    api<any>(`/api/chat/chatrooms/${chatroomId}/chats/${chatId}`),
  deleteChat: (chatroomId: string, chatId: string) =>
    api<void>(`/api/chat/chatrooms/${chatroomId}/chats/${chatId}`, { method: "DELETE" }),
  updateChat: (chatroomId: string, chatId: string, data: any) =>
    api<any>(`/api/chat/chatrooms/${chatroomId}/chats/${chatId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  getMessages: (chatroomId: string, chatId: string) =>
    api<any[]>(`/api/chat/chatrooms/${chatroomId}/chats/${chatId}/messages`),
  sendMessage: (chatroomId: string, chatId: string, content: string) =>
    api<any>(`/api/chat/chatrooms/${chatroomId}/chats/${chatId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
  exportChatroom: (id: string, opts: { include_annotations?: boolean } = {}) =>
    api<any>(`/api/chat/chatrooms/${id}/export`, {
      method: "POST",
      body: JSON.stringify({ include_annotations: opts.include_annotations ?? true }),
    }),
  exportChat: (
    chatroomId: string,
    chatId: string,
    opts: { include_annotations?: boolean; turn_ids?: string[] } = {},
  ) =>
    api<any>(`/api/chat/chatrooms/${chatroomId}/chats/${chatId}/export`, {
      method: "POST",
      body: JSON.stringify({
        include_annotations: opts.include_annotations ?? true,
        turn_ids: opts.turn_ids ?? null,
      }),
    }),
  importChatroom: (data: any) =>
    api<any>("/api/chat/chatrooms/import", {
      method: "POST",
      body: JSON.stringify({ data }),
    }),
  listAnnotations: (chatroomId: string, chatId: string) =>
    api<any[]>(`/api/chat/chatrooms/${chatroomId}/chats/${chatId}/annotations`),
  createAnnotation: (chatroomId: string, chatId: string, data: any) =>
    api<any>(`/api/chat/chatrooms/${chatroomId}/chats/${chatId}/annotations`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateAnnotation: (chatroomId: string, chatId: string, annotationId: string, data: any) =>
    api<any>(`/api/chat/chatrooms/${chatroomId}/chats/${chatId}/annotations/${annotationId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteAnnotation: (chatroomId: string, chatId: string, annotationId: string) =>
    api<void>(`/api/chat/chatrooms/${chatroomId}/chats/${chatId}/annotations/${annotationId}`, {
      method: "DELETE",
    }),
};
