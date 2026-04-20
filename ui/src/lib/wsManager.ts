import { useChatStore } from "@/stores/chatStore";

const connections = new Map<string, WebSocket>();

function key(chatroomId: string, chatId: string) {
  return `${chatroomId}:${chatId}`;
}

export function connect(chatroomId: string, chatId: string) {
  const k = key(chatroomId, chatId);
  const existing = connections.get(k);
  if (existing && existing.readyState <= WebSocket.OPEN) return;

  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${proto}//${window.location.host}/ws/chat/${chatroomId}/${chatId}`);

  ws.onmessage = (e) => {
    const s = useChatStore.getState();
    const msg = JSON.parse(e.data);
    const responseIndex = msg.response_index ?? 0;

    if (msg.type === "chunk" && !msg.done) {
      if (!s.streamingChatId) s.setStreamingChatId(chatId);
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
    } else if (msg.type === "turn_start") {
      if (!s.streamingChatId) s.setStreamingChatId(chatId);
      s.addMessage({
        id: msg.turn_id,
        role: "user",
        content: msg.content,
        created_at: new Date().toISOString(),
        responses: [],
      });
    } else if (msg.type === "turn_complete") {
      const exists = s.messages.some(m => m.id === msg.turn.id);
      if (exists) {
        s.updateMessage(msg.turn.id, msg.turn);
      } else {
        s.addMessage(msg.turn);
      }
      s.clearStream();
      // Auto-cleanup: close connection if this chat is not active
      if (s.activeChatId !== chatId) {
        disconnect(chatroomId, chatId);
      }
    } else if (msg.type === "turn_updated") {
      s.updateMessage(msg.turn_id, msg.turn);
      s.clearStream();
      if (s.activeChatId !== chatId) {
        disconnect(chatroomId, chatId);
      }
    } else if (msg.type === "error") {
      s.setStreamChunk(msg.model_id, responseIndex, `[Error] ${msg.error}`);
      s.setStreamDone(msg.model_id, responseIndex);
    }
  };

  ws.onerror = () => {
    console.error(`WebSocket error for ${k}`);
  };

  ws.onclose = () => {
    connections.delete(k);
  };

  connections.set(k, ws);
}

export function disconnect(chatroomId: string, chatId: string) {
  const k = key(chatroomId, chatId);
  const ws = connections.get(k);
  if (ws) {
    ws.close();
    connections.delete(k);
  }
}

export function send(chatroomId: string, chatId: string, payload: unknown): boolean {
  const k = key(chatroomId, chatId);
  const ws = connections.get(k);
  if (ws?.readyState === WebSocket.OPEN) {
    useChatStore.getState().clearStream();
    ws.send(JSON.stringify(payload));
    return true;
  }
  return false;
}

export function isConnected(chatroomId: string, chatId: string): boolean {
  const ws = connections.get(key(chatroomId, chatId));
  return ws?.readyState === WebSocket.OPEN;
}
