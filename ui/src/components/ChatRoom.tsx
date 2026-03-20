import { useEffect, useRef, useState } from "react";
import { useChatStore } from "@/stores/chatStore";
import { apiClient } from "@/lib/api";
import { useChat } from "@/hooks/useChat";
import { ResponseCard } from "./ResponseCard";
import { ResponseCarousel } from "./ResponseCarousel";
import { ModelConfig } from "./ModelConfig";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { CaretDown } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";
import type { Chatroom, Chat, ModelConfig as MC } from "@/stores/chatStore";

export function ChatRoom() {
  const {
    activeChatroomId, activeChatId,
    messages, setMessages, streaming,
    providers, setProviders,
  } = useChatStore();
  const { connect, disconnect, send: wsSend } = useChat();
  const [chatroom, setChatroom] = useState<Chatroom | null>(null);
  const [chat, setChat] = useState<Chat | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const prevStreaming = useRef(false);

  // Load chatroom meta when chatroom changes
  useEffect(() => {
    if (!activeChatroomId) { setChatroom(null); return; }
    apiClient.getChatroom(activeChatroomId).then(setChatroom).catch(console.error);
    apiClient.listProviders().then(setProviders).catch(console.error);
  }, [activeChatroomId, setProviders]);

  // Load chat meta + messages + WS when chat changes
  useEffect(() => {
    if (!activeChatroomId || !activeChatId) {
      setChat(null); setMessages([]); disconnect(); return;
    }
    Promise.all([
      apiClient.getChat(activeChatroomId, activeChatId),
      apiClient.getMessages(activeChatroomId, activeChatId),
    ]).then(([c, m]) => {
      setChat(c);
      setMessages(m);
      connect(activeChatroomId, activeChatId);
    }).catch(console.error);
    return () => disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeChatroomId, activeChatId]);

  // Detect streaming finish → show scroll button instead of forcing scroll
  const streamEntries = Object.values(streaming);
  const isStreaming = streamEntries.length > 0 && streamEntries.some(s => !s.done);

  useEffect(() => {
    if (prevStreaming.current && !isStreaming && streamEntries.length > 0) {
      setShowScrollBtn(true);
    }
    prevStreaming.current = isStreaming;
  }, [isStreaming, streamEntries.length]);

  const handleScroll = (e: React.UIEvent) => {
    const el = e.currentTarget;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 100) setShowScrollBtn(false);
  };

  // No chatroom selected
  if (!activeChatroomId) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        Select or create a chatroom to start comparing models
      </div>
    );
  }

  // Chatroom selected but no chat
  if (!activeChatId) {
    return (
      <div className="flex-1 flex flex-col h-full">
        <div className="flex items-center justify-between px-4 py-2 border-b border-border">
          <span className="font-medium">{chatroom?.name || "Chatroom"}</span>
          <div className="flex gap-2 items-center">
            <span className="text-xs text-muted-foreground">
              {chatroom?.models?.length || 0} model(s)
            </span>
            <Button size="sm" variant="outline" onClick={() => setShowConfig(!showConfig)} className="h-7 text-xs">
              {showConfig ? "Hide Config" : "Configure"}
            </Button>
          </div>
        </div>
        <div className="flex flex-1 overflow-hidden">
          {showConfig ? (
            <div className="flex-1 p-4 overflow-auto">
              <ModelConfig
                models={chatroom?.models || []}
                providers={providers}
                onUpdate={updateModels}
              />
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-muted-foreground">
              Create a chat to start a conversation, or configure models for this chatroom
            </div>
          )}
        </div>
      </div>
    );
  }

  async function updateModels(models: MC[]) {
    if (!activeChatroomId) return;
    const updated = await apiClient.updateChatroom(activeChatroomId, { models });
    setChatroom(updated);
  }

  // Use chat's snapshot for display, fall back to chatroom models
  const displayModels = chat?.models_snapshot || chatroom?.models || [];
  const modelMap = Object.fromEntries(displayModels.map((m) => [m.id, m]));

  const send = async () => {
    const text = input.trim();
    if (!text || sending || !activeChatroomId || !activeChatId) return;
    setInput("");
    setSending(true);
    try {
      const sent = wsSend(text);
      if (!sent) {
        const turn = await apiClient.sendMessage(activeChatroomId, activeChatId, text);
        useChatStore.getState().addMessage(turn);
      }
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full min-w-0">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="font-medium">{chatroom?.name}</span>
          <span className="text-xs text-muted-foreground">/ {chat?.name}</span>
        </div>
        <div className="flex gap-2 items-center">
          <span className="text-xs text-muted-foreground">
            {displayModels.length} model(s)
          </span>
          {chat && chatroom && chatroom.models.length !== chat.models_snapshot.length && (
            <span className="text-[10px] text-amber-500" title="Start a new chat to use updated models">
              (chatroom has {chatroom.models.length})
            </span>
          )}
          <Button size="sm" variant="outline" onClick={() => setShowConfig(!showConfig)} className="h-7 text-xs">
            {showConfig ? "Hide Config" : "Configure"}
          </Button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <ScrollArea className="flex-1 min-w-0 p-4" onScrollCapture={handleScroll}>
          <div className="space-y-6">
            {messages.map((msg) => (
              <div key={msg.id} className="space-y-2">
                <div className="text-sm font-medium">You</div>
                <div className="text-sm bg-muted/30 rounded-md p-3">{msg.content}</div>
                <ResponseCarousel>
                  {msg.responses.map((r) => (
                    <ResponseCard
                      key={r.model_id}
                      modelName={modelMap[r.model_id]?.display_name || r.model_id}
                      content={r.content}
                      metadata={r}
                      error={r.error}
                    />
                  ))}
                </ResponseCarousel>
              </div>
            ))}

            {Object.keys(streaming).length > 0 && (
              <div className="space-y-2">
                <div className="text-sm font-medium">You</div>
                <ResponseCarousel>
                  {Object.entries(streaming).map(([mid, s]) => (
                    <ResponseCard
                      key={mid}
                      modelName={modelMap[mid]?.display_name || mid}
                      content={s.content}
                      streaming={!s.done}
                      metadata={s.done ? s.metadata : undefined}
                    />
                  ))}
                </ResponseCarousel>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>

        <div className={cn(
          "border-l border-border overflow-hidden transition-[width] duration-200",
          showConfig ? "w-72" : "w-0"
        )}>
          {showConfig && (
            <div className="w-72 p-3 overflow-auto h-full">
              <div className="mb-3">
                <p className="text-[10px] text-muted-foreground">
                  Editing chatroom config. Changes apply to new chats only.
                </p>
              </div>
              <ModelConfig
                models={chatroom?.models || []}
                providers={providers}
                onUpdate={updateModels}
              />
            </div>
          )}
        </div>
      </div>

      {showScrollBtn && (
        <div className="flex justify-center py-1">
          <button
            onClick={() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); setShowScrollBtn(false); }}
            className="flex items-center gap-1 px-3 py-1 rounded-full bg-muted text-muted-foreground text-xs hover:bg-muted/80 animate-in fade-in"
          >
            <CaretDown size={14} /> New responses
          </button>
        </div>
      )}
      <Separator />
      <div className="p-3 flex gap-2">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
          }}
          placeholder="Send a prompt to all models..."
          rows={2}
          className="resize-none text-sm"
        />
        <Button onClick={send} disabled={sending || !input.trim()} className="self-end">
          {sending ? "..." : "Send"}
        </Button>
      </div>
    </div>
  );
}
