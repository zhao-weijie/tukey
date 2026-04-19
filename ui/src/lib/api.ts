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
  // Chatrooms
  listChatrooms: () => api<any[]>("/api/chat/chatrooms"),
  createChatroom: (name: string, models: any[] = []) =>
    api<any>("/api/chat/chatrooms", {
      method: "POST",
      body: JSON.stringify({ name, models }),
    }),
  getChatroom: (id: string) => api<any>(`/api/chat/chatrooms/${id}`),
  updateChatroom: (id: string, data: any) =>
    api<any>(`/api/chat/chatrooms/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteChatroom: (id: string) =>
    api<void>(`/api/chat/chatrooms/${id}`, { method: "DELETE" }),

  // Chats
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

  // Messages
  getMessages: (chatroomId: string, chatId: string) =>
    api<any[]>(`/api/chat/chatrooms/${chatroomId}/chats/${chatId}/messages`),
  sendMessage: (chatroomId: string, chatId: string, content: string) =>
    api<any>(`/api/chat/chatrooms/${chatroomId}/chats/${chatId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  // Providers
  listProviders: () => api<any[]>("/api/config/providers"),
  createProvider: (data: any) =>
    api<any>("/api/config/providers", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateProvider: (id: string, data: Record<string, any>) =>
    api<any>(`/api/config/providers/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteProvider: (id: string) =>
    api<void>(`/api/config/providers/${id}`, { method: "DELETE" }),
  testProvider: (id: string) =>
    api<{ ok: boolean; error?: string }>(`/api/config/providers/${id}/test`, {
      method: "POST",
    }),

  // Search
  search: (q: string, limit = 50) =>
    api<{ results: any[] }>(`/api/search?q=${encodeURIComponent(q)}&limit=${limit}`),

  // Export / Import
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

  // Models
  getModelCapabilities: (modelId: string) =>
    api<{
      supports_reasoning: boolean;
      supports_vision: boolean;
      max_tokens: number | null;
      max_input_tokens: number | null;
    }>(`/api/models/${encodeURIComponent(modelId)}/capabilities`),
  getAvailableModels: (providerId: string) =>
    api<{ id: string; name: string }[]>(`/api/models/providers/${providerId}/available`),

  // Chat Annotations
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

  // Quick setup (onboarding)
  quickSetup: (data: {
    api_key: string;
    provider?: string;
    base_url?: string | null;
    display_name?: string | null;
    models?: { model_id: string; display_name?: string }[];
    chatroom_name?: string;
  }) =>
    api<{ provider: any; chatroom: any; chat: any }>("/api/config/quick-setup", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // MCP Servers
  listMcpServers: () => api<any[]>("/api/config/mcp-servers"),
  createMcpServer: (data: { name: string; command: string; args?: string[]; env?: Record<string, string> }) =>
    api<any>("/api/config/mcp-servers", {
      method: "POST",
      body: JSON.stringify(data),
    }),
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
      { method: "POST" }
    ),

  // Health
  getHealth: () => api<{ status: string; data_dir: string }>("/api/health"),

  // Data directory
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
};
