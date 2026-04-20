import { useCallback } from "react";
import { useChatStore } from "@/stores/chatStore";
import * as wsManager from "@/lib/wsManager";

export function useChat() {
  const connect = useCallback((chatroomId: string, chatId: string) => {
    wsManager.connect(chatroomId, chatId);
  }, []);

  const disconnect = useCallback((chatroomId: string, chatId: string) => {
    wsManager.disconnect(chatroomId, chatId);
  }, []);

  const send = useCallback(
    (content: string, n: number = 1, responseIndices?: Record<string, number>) => {
      const { activeChatroomId, activeChatId } = useChatStore.getState();
      if (!activeChatroomId || !activeChatId) return false;
      return wsManager.send(activeChatroomId, activeChatId, {
        content, n, response_indices: responseIndices,
      });
    },
    []
  );

  const regenerate = useCallback((turnId: string, n: number = 1) => {
    const { activeChatroomId, activeChatId } = useChatStore.getState();
    if (!activeChatroomId || !activeChatId) return false;
    return wsManager.send(activeChatroomId, activeChatId, {
      type: "regenerate", turn_id: turnId, n,
    });
  }, []);

  return { connect, disconnect, send, regenerate };
}
