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
}

export interface ResponseMeta {
  model_id: string;
  content: string;
  tokens_in: number;
  tokens_out: number;
  cost: number;
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

interface StreamState {
  [modelId: string]: { content: string; done: boolean; metadata?: Partial<ResponseMeta> };
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
  setProviders: (providers: Provider[]) => void;

  setStreamChunk: (modelId: string, delta: string) => void;
  setStreamDone: (modelId: string, metadata?: Partial<ResponseMeta>) => void;
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
  setActiveChatroom: (id) => set({ activeChatroomId: id, chats: [], activeChatId: null, messages: [] }),
  setChats: (chats) => set({ chats }),
  setActiveChat: (id) => set({ activeChatId: id, messages: [] }),
  setMessages: (msgs) => set({ messages: msgs }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setProviders: (providers) => set({ providers }),

  setStreamChunk: (modelId, delta) =>
    set((s) => {
      const prev = s.streaming[modelId] || { content: "", done: false };
      return {
        streaming: {
          ...s.streaming,
          [modelId]: { ...prev, content: prev.content + delta },
        },
      };
    }),
  setStreamDone: (modelId, metadata) =>
    set((s) => ({
      streaming: {
        ...s.streaming,
        [modelId]: { ...s.streaming[modelId], done: true, metadata },
      },
    })),
  clearStream: () => set({ streaming: {} }),
}));
