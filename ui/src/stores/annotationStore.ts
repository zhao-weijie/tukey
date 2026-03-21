import { create } from "zustand";
import { apiClient } from "@/lib/api";

export interface Annotation {
  id: string;
  message_id: string;
  model_id: string;
  response_index: number;
  exact: string;
  prefix: string;
  suffix: string;
  rating: "positive" | "negative";
  comment: string;
  created_at: string;
  updated_at: string;
}

interface AnnotationState {
  annotations: Record<string, Annotation[]>; // keyed by chatId

  fetchAnnotations: (chatroomId: string, chatId: string) => Promise<void>;
  addAnnotation: (
    chatroomId: string,
    chatId: string,
    data: Omit<Annotation, "id" | "created_at" | "updated_at">
  ) => Promise<Annotation>;
  updateAnnotation: (
    chatroomId: string,
    chatId: string,
    annotationId: string,
    data: { rating?: string; comment?: string }
  ) => Promise<void>;
  deleteAnnotation: (
    chatroomId: string,
    chatId: string,
    annotationId: string
  ) => Promise<void>;
}

export const useAnnotationStore = create<AnnotationState>((set) => ({
  annotations: {},

  fetchAnnotations: async (chatroomId, chatId) => {
    const data = await apiClient.listAnnotations(chatroomId, chatId);
    set((s) => ({
      annotations: { ...s.annotations, [chatId]: data },
    }));
  },

  addAnnotation: async (chatroomId, chatId, data) => {
    const ann = await apiClient.createAnnotation(chatroomId, chatId, data);
    set((s) => ({
      annotations: {
        ...s.annotations,
        [chatId]: [...(s.annotations[chatId] || []), ann],
      },
    }));
    return ann;
  },

  updateAnnotation: async (chatroomId, chatId, annotationId, data) => {
    const updated = await apiClient.updateAnnotation(
      chatroomId,
      chatId,
      annotationId,
      data
    );
    set((s) => ({
      annotations: {
        ...s.annotations,
        [chatId]: (s.annotations[chatId] || []).map((a) =>
          a.id === annotationId ? updated : a
        ),
      },
    }));
  },

  deleteAnnotation: async (chatroomId, chatId, annotationId) => {
    await apiClient.deleteAnnotation(chatroomId, chatId, annotationId);
    set((s) => ({
      annotations: {
        ...s.annotations,
        [chatId]: (s.annotations[chatId] || []).filter(
          (a) => a.id !== annotationId
        ),
      },
    }));
  },
}));
