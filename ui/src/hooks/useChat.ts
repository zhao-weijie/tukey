import { useCallback, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";

export function useChat() {
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback((chatroomId: string, chatId: string) => {
    if (wsRef.current) wsRef.current.close();
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${proto}//${window.location.host}/ws/chat/${chatroomId}/${chatId}`);

    ws.onmessage = (e) => {
      const s = useChatStore.getState();
      const msg = JSON.parse(e.data);
      const responseIndex = msg.response_index ?? 0;
      if (msg.type === "chunk" && !msg.done) {
        s.setStreamChunk(msg.model_id, responseIndex, msg.delta);
      } else if (msg.type === "chunk" && msg.done) {
        s.setStreamDone(msg.model_id, responseIndex, msg.metadata);
      } else if (msg.type === "tool_call") {
        const tc = msg.tool_call;
        s.setStreamToolCall(msg.model_id, responseIndex, {
          id: tc.id, name: tc.name, arguments: tc.arguments,
        });
      } else if (msg.type === "tool_result") {
        const tr = msg.tool_result;
        s.setStreamToolResult(msg.model_id, responseIndex, {
          toolCallId: tr.tool_call_id, name: tr.name,
          result: tr.result, error: tr.error,
        });
      } else if (msg.type === "turn_complete") {
        s.addMessage(msg.turn);
        s.clearStream();
      } else if (msg.type === "turn_updated") {
        s.updateMessage(msg.turn_id, msg.turn);
        s.clearStream();
      } else if (msg.type === "error") {
        s.setStreamChunk(msg.model_id, responseIndex, `[Error] ${msg.error}`);
        s.setStreamDone(msg.model_id, responseIndex);
      }
    };

    ws.onerror = () => {
      console.error("WebSocket error, falling back to HTTP");
    };

    wsRef.current = ws;
  }, []);

  const send = useCallback(
    (content: string, n: number = 1, responseIndices?: Record<string, number>) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        useChatStore.getState().clearStream();
        wsRef.current.send(
          JSON.stringify({ content, n, response_indices: responseIndices })
        );
        return true;
      }
      return false;
    },
    []
  );

  const regenerate = useCallback((turnId: string, n: number = 1) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      useChatStore.getState().clearStream();
      wsRef.current.send(
        JSON.stringify({ type: "regenerate", turn_id: turnId, n })
      );
      return true;
    }
    return false;
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  return { connect, disconnect, send, regenerate };
}
