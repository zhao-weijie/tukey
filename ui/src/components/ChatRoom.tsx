import { useEffect, useRef, useState } from "react";
import { useChatStore } from "@/stores/chatStore";
import { apiClient } from "@/lib/api";
import { useChat } from "@/hooks/useChat";
import { ResponseCard } from "./ResponseCard";
import { ResponseCarousel } from "./ResponseCarousel";
import { ModelConfig } from "./ModelConfig";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { CaretDown, CaretUp, ArrowsClockwise } from "@phosphor-icons/react";
import { useAnnotationStore } from "@/stores/annotationStore";
import type { Chatroom, Chat, ModelConfig as MC, ResponseMeta } from "@/stores/chatStore";

function groupResponsesByModel(responses: ResponseMeta[]): Record<string, ResponseMeta[]> {
  const groups: Record<string, ResponseMeta[]> = {};
  for (const r of responses) {
    (groups[r.model_id] ||= []).push(r);
  }
  for (const key of Object.keys(groups)) {
    groups[key].sort((a, b) => (a.response_index ?? 0) - (b.response_index ?? 0));
  }
  return groups;
}

interface ChatRoomProps {
  demoPrompt?: string | null;
  onDemoPromptUsed?: () => void;
}

export function ChatRoom({ demoPrompt, onDemoPromptUsed }: ChatRoomProps = {}) {
  const {
    activeChatroomId, activeChatId,
    messages, setMessages, streaming, streamingChatId,
    providers, setProviders,
    mcpServers,
  } = useChatStore();
  const { connect, send: wsSend, regenerate: wsRegenerate } = useChat();
  const [chatroom, setChatroom] = useState<Chatroom | null>(null);
  const [chat, setChat] = useState<Chat | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const prevStreaming = useRef(false);
  const [completionCount, setCompletionCount] = useState(1);
  // Cycling state: { [turnId]: { [modelId]: activeIndex } }
  const [cyclingState, setCyclingState] = useState<Record<string, Record<string, number>>>({});
  // Regenerate UI state: which turn_id has the inline form open
  const [regenTurnId, setRegenTurnId] = useState<string | null>(null);
  const [regenCount, setRegenCount] = useState(1);
  const { fetchAnnotations } = useAnnotationStore();

  // Pre-fill demo prompt from onboarding
  useEffect(() => {
    if (demoPrompt && activeChatId) {
      setInput(demoPrompt);
      onDemoPromptUsed?.();
    }
  }, [demoPrompt, activeChatId]);

  // Load chatroom meta when chatroom changes
  useEffect(() => {
    if (!activeChatroomId) { setChatroom(null); return; }
    apiClient.getChatroom(activeChatroomId).then(setChatroom).catch(console.error);
    apiClient.listProviders().then(setProviders).catch(console.error);
  }, [activeChatroomId, setProviders]);

  // Load chat meta + messages + WS when chat changes
  useEffect(() => {
    if (!activeChatroomId || !activeChatId) {
      setChat(null); setMessages([]); return;
    }
    Promise.all([
      apiClient.getChat(activeChatroomId, activeChatId),
      apiClient.getMessages(activeChatroomId, activeChatId),
    ]).then(([c, m]) => {
      setChat(c);
      setMessages(m);
      connect(activeChatroomId, activeChatId);
      fetchAnnotations(activeChatroomId, activeChatId).catch(console.error);
    }).catch(console.error);
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
        {showConfig ? (
          <div className="flex-1 flex flex-col min-h-0 min-w-0 overflow-hidden p-4">
            <div className="flex-1 min-h-0 min-w-0">
              <ModelConfig
                models={chatroom?.models || []}
                providers={providers}
                mcpServers={mcpServers}
                onUpdate={updateModels}
              />
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            Create a chat to start a conversation, or configure models for this chatroom
          </div>
        )}
      </div>
    );
  }

  async function updateModels(models: MC[]) {
    if (!activeChatroomId) return;
    const updated = await apiClient.updateChatroom(activeChatroomId, { models });
    setChatroom(updated);
  }

  // Before any messages, show the chatroom's live models so config changes
  // are reflected immediately. Once messages exist, lock to the snapshot.
  const displayModels = (messages.length === 0 && chatroom?.models)
    ? chatroom.models
    : (chat?.models_snapshot || chatroom?.models || []);
  const modelMap = Object.fromEntries(displayModels.map((m) => [m.id, m]));

  // Collect currently-viewed response indices for multi-turn context
  function getResponseIndices(): Record<string, number> {
    const indices: Record<string, number> = {};
    for (const msg of messages) {
      const turnCycling = cyclingState[msg.id];
      if (turnCycling) {
        // For each model in this turn, record the viewed index
        for (const [, idx] of Object.entries(turnCycling)) {
          indices[msg.id] = idx; // last model's idx wins per turn — we use turn-level index
        }
      }
    }
    return indices;
  }

  const send = async () => {
    const text = input.trim();
    if (!text || sending || !activeChatroomId || !activeChatId) return;
    setInput("");
    setSending(true);
    try {
      const responseIndices = getResponseIndices();
      const sent = wsSend(text, completionCount, responseIndices);
      if (!sent) {
        const turn = await apiClient.sendMessage(activeChatroomId, activeChatId, text);
        useChatStore.getState().addMessage(turn);
      }
    } finally {
      setSending(false);
    }
  };

  function handleCyclingChange(turnId: string, modelId: string, index: number) {
    setCyclingState((prev) => ({
      ...prev,
      [turnId]: { ...prev[turnId], [modelId]: index },
    }));
  }

  function handleRegenerate(turnId: string) {
    wsRegenerate(turnId, regenCount);
    setRegenTurnId(null);
    setRegenCount(1);
  }

  // Group streaming entries by modelId for display
  function groupStreamByModel(): Record<string, { content: string; total: number; toolCalls?: import("@/stores/chatStore").ToolCallEntry[]; toolResults?: import("@/stores/chatStore").ToolResultEntry[] }> {
    const groups: Record<string, { content: string; total: number; minIdx: number; toolCalls?: import("@/stores/chatStore").ToolCallEntry[]; toolResults?: import("@/stores/chatStore").ToolResultEntry[] }> = {};
    for (const entry of Object.values(streaming)) {
      const mid = entry.modelId;
      if (!groups[mid]) {
        groups[mid] = { content: entry.content, total: 1, minIdx: entry.responseIndex, toolCalls: entry.toolCalls, toolResults: entry.toolResults };
      } else {
        groups[mid].total++;
        if (entry.responseIndex < groups[mid].minIdx) {
          groups[mid] = { ...groups[mid], content: entry.content, minIdx: entry.responseIndex, toolCalls: entry.toolCalls, toolResults: entry.toolResults };
        }
      }
    }
    return groups;
  }

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
          {chat && chatroom && (() => {
            const snapshotIds = new Set(chat.models_snapshot.map((m) => m.id));
            const chatroomIds = new Set(chatroom.models.map((m) => m.id));
            const stale = snapshotIds.size !== chatroomIds.size || [...snapshotIds].some((id) => !chatroomIds.has(id));
            if (!stale) return null;
            return (
              <button
                className="text-[10px] text-amber-500 hover:text-amber-400 cursor-pointer"
                title="Click to update this chat's models to match the chatroom"
                onClick={async () => {
                  if (!activeChatroomId || !activeChatId) return;
                  const updatedChat = await apiClient.updateChat(
                    activeChatroomId, activeChatId,
                    { models_snapshot: chatroom.models }
                  );
                  setChat(updatedChat);
                }}
              >
                models changed — click to update
              </button>
            );
          })()}
          <Button size="sm" variant="outline" onClick={() => setShowConfig(!showConfig)} className="h-7 text-xs">
            {showConfig ? "Hide Config" : "Configure"}
          </Button>
        </div>
      </div>

      {showConfig ? (
        <div className="flex-1 flex flex-col min-h-0 min-w-0 overflow-hidden px-4 pt-3 pb-0">
          <p className="text-[10px] text-muted-foreground flex-shrink-0 mb-2">
            Editing chatroom config. Changes apply to new chats only.
          </p>
          <div className="flex-1 min-h-0 min-w-0">
            <ModelConfig
              models={chatroom?.models || []}
              providers={providers}
              mcpServers={mcpServers}
              onUpdate={updateModels}
            />
          </div>
        </div>
      ) : (
        <ScrollArea className="flex-1 min-w-0 min-h-0 p-4" onScrollCapture={handleScroll}>
          <div className="space-y-6">
            {messages.map((msg, msgIdx) => {
              const grouped = groupResponsesByModel(msg.responses);
              const modelIds = Object.keys(grouped);
              const nextMsg = msgIdx < messages.length - 1 ? messages[msgIdx + 1] : null;
              return (
                <div key={msg.id} className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="text-sm font-medium">You</div>
                    <button
                      onClick={() => setRegenTurnId(regenTurnId === msg.id ? null : msg.id)}
                      className="p-0.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                      title="Generate more completions"
                    >
                      <ArrowsClockwise size={14} />
                    </button>
                  </div>
                  <div className="text-sm bg-muted/30 rounded-md p-3 whitespace-pre-wrap">{msg.content}</div>
                  {regenTurnId === msg.id && (
                    <div className="flex items-center gap-2 pl-1">
                      <span className="text-xs text-muted-foreground">Add</span>
                      <Input
                        type="number"
                        min={1}
                        max={9}
                        value={regenCount}
                        onChange={(e) => setRegenCount(Math.min(9, Math.max(1, Number(e.target.value) || 1)))}
                        className="w-12 h-6 text-xs text-center"
                      />
                      <span className="text-xs text-muted-foreground">more</span>
                      <Button
                        size="sm"
                        className="h-6 text-xs px-2"
                        onClick={() => handleRegenerate(msg.id)}
                      >
                        Go
                      </Button>
                    </div>
                  )}
                  {msg.responses.length === 0 && streamingChatId !== activeChatId ? (
                    <ResponseCarousel>
                      {displayModels.map((m) => (
                        <div key={m.id} className="min-w-0 border border-border rounded-lg flex flex-col h-32 animate-pulse">
                          <div className="flex items-center px-3 py-2 border-b border-border bg-muted/30">
                            <div className="h-4 w-24 bg-muted rounded" />
                          </div>
                          <div className="flex-1 p-3 space-y-2">
                            <div className="h-3 w-full bg-muted/50 rounded" />
                            <div className="h-3 w-3/4 bg-muted/50 rounded" />
                            <div className="h-3 w-1/2 bg-muted/50 rounded" />
                          </div>
                        </div>
                      ))}
                    </ResponseCarousel>
                  ) : msg.responses.length > 0 ? (
                    <ResponseCarousel>
                      {modelIds.map((mid) => (
                        <ResponseCard
                          key={mid}
                          modelName={modelMap[mid]?.display_name || mid}
                          responses={grouped[mid]}
                          activeIndex={cyclingState[msg.id]?.[mid] ?? 0}
                          onIndexChange={(idx) => handleCyclingChange(msg.id, mid, idx)}
                          messageId={msg.id}
                          chatroomId={activeChatroomId!}
                          chatId={activeChatId!}
                          continuationIndex={nextMsg ? nextMsg.response_indices?.[msg.id] ?? 0 : undefined}
                        />
                      ))}
                    </ResponseCarousel>
                  ) : null}
                </div>
              );
            })}

            {Object.keys(streaming).length > 0 && streamingChatId === activeChatId && (
              <div className="space-y-2">
                <ResponseCarousel>
                  {Object.entries(groupStreamByModel()).map(([mid, { content, total, toolCalls, toolResults }]) => (
                    <ResponseCard
                      key={mid}
                      modelName={modelMap[mid]?.display_name || mid}
                      responses={[]}
                      activeIndex={0}
                      onIndexChange={() => {}}
                      streaming
                      streamingContent={content}
                      streamingTotal={total}
                      streamingToolCalls={toolCalls}
                      streamingToolResults={toolResults}
                    />
                  ))}
                </ResponseCarousel>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>
      )}

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
      <div className="p-3 flex gap-2 items-end">
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
        <div className="flex flex-col items-center gap-1">
          <div className="flex flex-col items-center">
            <button
              onClick={() => setCompletionCount((c) => Math.min(9, c + 1))}
              className="p-0 leading-none text-muted-foreground hover:text-foreground"
              aria-label="Increase completions"
            >
              <CaretUp size={14} />
            </button>
            <span className="text-xs tabular-nums leading-tight" title="Completions per model per turn">
              &times;{completionCount}
            </span>
            <button
              onClick={() => setCompletionCount((c) => Math.max(1, c - 1))}
              className="p-0 leading-none text-muted-foreground hover:text-foreground"
              aria-label="Decrease completions"
            >
              <CaretDown size={14} />
            </button>
          </div>
        </div>
        <Button onClick={send} disabled={sending || !input.trim()} className="self-end">
          {sending ? "..." : <>Send <kbd className="ml-1 text-[10px] opacity-50">&#x21B5;</kbd></>}
        </Button>
      </div>
    </div>
  );
}
