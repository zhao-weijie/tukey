import { create } from "zustand";

export interface Provider {
  id: string;
  provider: string;
  api_key: string;
  base_url?: string | null;
  display_name?: string;
}

export interface ModelConfig {
  id: string;
  provider_id: string;
  model_id: string;
  display_name: string;
  system_prompt: string;
  temperature: number;
  max_tokens?: number | null;
  top_p?: number | null;
  extra_params: Record<string, unknown>;
  response_format?: { type: string; json_schema?: Record<string, unknown> } | null;
  tools?: Record<string, unknown>[] | null;
  tool_choice?: string | { type: string; function: { name: string } } | null;
}

export interface ResponseMeta {
  model_id: string;
  response_index: number;
  content: string;
  tokens_in: number;
  tokens_out: number;
  cost: number | null;
  duration_ms: number;
  tokens_per_sec: number;
  error?: boolean;
}

export interface Message {
  id: string;
  role: string;
  content: string;
  created_at: string;
  responses: ResponseMeta[];
  response_indices?: Record<string, number>;
}

export interface Chatroom {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  models: ModelConfig[];
}

export interface Chat {
  id: string;
  name: string;
  models_snapshot: ModelConfig[];
  created_at: string;
}

interface StreamEntry {
  content: string;
  done: boolean;
  metadata?: Partial<ResponseMeta>;
  modelId: string;
  responseIndex: number;
}

interface StreamState {
  [key: string]: StreamEntry; // key = `${modelId}:${responseIndex}`
}

interface ChatState {
  chatrooms: Chatroom[];
  activeChatroomId: string | null;
  chats: Chat[];
  activeChatId: string | null;
  messages: Message[];
  streaming: StreamState;
  providers: Provider[];

  setChatrooms: (chatrooms: Chatroom[]) => void;
  setActiveChatroom: (id: string | null) => void;
  setChats: (chats: Chat[]) => void;
  setActiveChat: (id: string | null) => void;
  setMessages: (msgs: Message[]) => void;
  addMessage: (msg: Message) => void;
  updateMessage: (turnId: string, msg: Message) => void;
  setProviders: (providers: Provider[]) => void;

  setStreamChunk: (modelId: string, responseIndex: number, delta: string) => void;
  setStreamDone: (modelId: string, responseIndex: number, metadata?: Partial<ResponseMeta>) => void;
  clearStream: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  chatrooms: [],
  activeChatroomId: null,
  chats: [],
  activeChatId: null,
  messages: [],
  streaming: {},
  providers: [],

  setChatrooms: (chatrooms) => set({ chatrooms }),
  setActiveChatroom: (id) => set((s) => s.activeChatroomId === id ? {} : { activeChatroomId: id, chats: [], activeChatId: null, messages: [] }),
  setChats: (chats) => set({ chats }),
  setActiveChat: (id) => set((s) => s.activeChatId === id ? {} : { activeChatId: id, messages: [] }),
  setMessages: (msgs) => set({ messages: msgs }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  updateMessage: (turnId, msg) =>
    set((s) => ({
      messages: s.messages.map((m) => (m.id === turnId ? msg : m)),
    })),
  setProviders: (providers) => set({ providers }),

  setStreamChunk: (modelId, responseIndex, delta) =>
    set((s) => {
      const key = `${modelId}:${responseIndex}`;
      const prev = s.streaming[key] || { content: "", done: false, modelId, responseIndex };
      return {
        streaming: {
          ...s.streaming,
          [key]: { ...prev, content: prev.content + delta, modelId, responseIndex },
        },
      };
    }),
  setStreamDone: (modelId, responseIndex, metadata) =>
    set((s) => {
      const key = `${modelId}:${responseIndex}`;
      return {
        streaming: {
          ...s.streaming,
          [key]: { ...s.streaming[key], done: true, metadata, modelId, responseIndex },
        },
      };
    }),
  clearStream: () => set({ streaming: {} }),
}));
