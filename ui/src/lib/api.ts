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
  listRooms: () => api<any[]>("/api/chat/rooms"),
  createRoom: (name: string, models: any[] = []) =>
    api<any>("/api/chat/rooms", {
      method: "POST",
      body: JSON.stringify({ name, models }),
    }),
  getRoom: (id: string) => api<any>(`/api/chat/rooms/${id}`),
  updateRoom: (id: string, data: any) =>
    api<any>(`/api/chat/rooms/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteRoom: (id: string) =>
    api<void>(`/api/chat/rooms/${id}`, { method: "DELETE" }),
  getMessages: (id: string) => api<any[]>(`/api/chat/rooms/${id}/messages`),
  sendMessage: (roomId: string, content: string) =>
    api<any>(`/api/chat/rooms/${roomId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  listProviders: () => api<any[]>("/api/config/providers"),
  createProvider: (data: any) =>
    api<any>("/api/config/providers", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteProvider: (id: string) =>
    api<void>(`/api/config/providers/${id}`, { method: "DELETE" }),
};
