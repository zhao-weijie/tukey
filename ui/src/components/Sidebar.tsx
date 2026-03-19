import { useEffect, useState, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { ProviderSetup } from "./ProviderSetup";
import { SearchDialog } from "./SearchDialog";
import type { Chatroom, Chat } from "@/stores/chatStore";

export function Sidebar() {
  const {
    chatrooms, setChatrooms,
    activeChatroomId, setActiveChatroom,
    chats, setChats,
    activeChatId, setActiveChat,
    providers, setProviders,
    setMessages,
  } = useChatStore();
  const [newName, setNewName] = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const importRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    apiClient.listChatrooms().then(setChatrooms).catch(console.error);
    apiClient.listProviders().then(setProviders).catch(console.error);
  }, [setChatrooms, setProviders]);

  // Load chats when a chatroom is expanded or selected
  useEffect(() => {
    if (!activeChatroomId) return;
    apiClient.listChats(activeChatroomId).then(setChats).catch(console.error);
  }, [activeChatroomId, setChats]);

  const createChatroom = async () => {
    const name = newName.trim() || "New Chatroom";
    const cr = await apiClient.createChatroom(name);
    setChatrooms([...chatrooms, cr]);
    setActiveChatroom(cr.id);
    setExpanded((e) => ({ ...e, [cr.id]: true }));
    setNewName("");
  };

  const deleteChatroom = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await apiClient.deleteChatroom(id);
    setChatrooms(chatrooms.filter((r) => r.id !== id));
    if (activeChatroomId === id) {
      setActiveChatroom(null);
      setActiveChat(null);
      setMessages([]);
    }
  };

  const toggleExpand = (id: string) => {
    setExpanded((e) => ({ ...e, [id]: !e[id] }));
  };

  const selectChatroom = (id: string) => {
    setActiveChatroom(id);
    setActiveChat(null);
    setExpanded((e) => ({ ...e, [id]: true }));
  };

  const createChat = async (chatroomId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const chat = await apiClient.createChat(chatroomId);
    if (activeChatroomId === chatroomId) {
      setChats([...chats, chat]);
    }
    setActiveChatroom(chatroomId);
    setActiveChat(chat.id);
    setExpanded((prev) => ({ ...prev, [chatroomId]: true }));
  };

  const deleteChat = async (chatroomId: string, chatId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await apiClient.deleteChat(chatroomId, chatId);
    setChats(chats.filter((c) => c.id !== chatId));
    if (activeChatId === chatId) {
      setActiveChat(null);
      setMessages([]);
    }
  };

  const exportChatroom = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const data = await apiClient.exportChatroom(id);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `tukey-export-${id.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    const data = JSON.parse(text);
    const cr = await apiClient.importChatroom(data);
    setChatrooms([...chatrooms, cr]);
    setActiveChatroom(cr.id);
    setExpanded((prev) => ({ ...prev, [cr.id]: true }));
    if (importRef.current) importRef.current.value = "";
  };

  const selectChat = (chatroomId: string, chatId: string) => {
    if (activeChatroomId !== chatroomId) {
      setActiveChatroom(chatroomId);
      // chats will reload via useEffect
    }
    setActiveChat(chatId);
  };

  return (
    <div className="w-64 border-r border-border flex flex-col h-full bg-sidebar">
      <div className="p-3 flex items-center justify-between">
        <span className="font-semibold text-lg text-sidebar-foreground">Tukey</span>
        <SearchDialog />
      </div>
      <Separator />
      <div className="p-2 flex gap-1">
        <Input
          placeholder="Chatroom name..."
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && createChatroom()}
          className="text-sm h-8"
        />
        <Button size="sm" onClick={createChatroom} className="h-8 px-3 shrink-0">+</Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => importRef.current?.click()}
          className="h-8 px-2 shrink-0 text-xs"
          title="Import chatroom"
        >
          Import
        </Button>
        <input
          ref={importRef}
          type="file"
          accept=".json"
          className="hidden"
          onChange={handleImport}
        />
      </div>
      <ScrollArea className="flex-1">
        <div className="p-1 space-y-0.5">
          {chatrooms.map((cr) => (
            <ChatroomItem
              key={cr.id}
              chatroom={cr}
              isActive={activeChatroomId === cr.id}
              isExpanded={!!expanded[cr.id]}
              activeChatId={activeChatId}
              chats={activeChatroomId === cr.id ? chats : []}
              onToggle={() => toggleExpand(cr.id)}
              onSelect={() => selectChatroom(cr.id)}
              onDelete={(e) => deleteChatroom(cr.id, e)}
              onExport={(e) => exportChatroom(cr.id, e)}
              onCreateChat={(e) => createChat(cr.id, e)}
              onSelectChat={(chatId) => selectChat(cr.id, chatId)}
              onDeleteChat={(chatId, e) => deleteChat(cr.id, chatId, e)}
            />
          ))}
        </div>
      </ScrollArea>
      <Separator />
      <div className="p-2">
        <ProviderSetup providers={providers} onUpdate={setProviders} />
      </div>
    </div>
  );
}

function ChatroomItem({
  chatroom, isActive, isExpanded, activeChatId, chats,
  onToggle, onSelect, onDelete, onExport, onCreateChat, onSelectChat, onDeleteChat,
}: {
  chatroom: Chatroom;
  isActive: boolean;
  isExpanded: boolean;
  activeChatId: string | null;
  chats: Chat[];
  onToggle: () => void;
  onSelect: () => void;
  onDelete: (e: React.MouseEvent) => void;
  onExport: (e: React.MouseEvent) => void;
  onCreateChat: (e: React.MouseEvent) => void;
  onSelectChat: (chatId: string) => void;
  onDeleteChat: (chatId: string, e: React.MouseEvent) => void;
}) {
  return (
    <div>
      <div
        onClick={() => { isActive ? onToggle() : onSelect(); }}
        className={`group flex items-center justify-between px-2 py-1.5 rounded-md cursor-pointer text-sm ${
          isActive && !activeChatId
            ? "bg-sidebar-accent text-sidebar-accent-foreground"
            : "text-sidebar-foreground hover:bg-sidebar-accent/50"
        }`}
      >
        <div className="flex items-center gap-1 truncate">
          <span className="text-xs text-muted-foreground">{isExpanded ? "▾" : "▸"}</span>
          <span className="truncate">{chatroom.name}</span>
          <span className="text-[10px] text-muted-foreground ml-1">
            {chatroom.models?.length || 0}m
          </span>
        </div>
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100">
          <button onClick={onCreateChat} className="text-muted-foreground hover:text-foreground text-xs px-1" title="New chat">+</button>
          <button onClick={onExport} className="text-muted-foreground hover:text-foreground text-xs px-1" title="Export chatroom">&#8615;</button>
          <button onClick={onDelete} className="text-muted-foreground hover:text-destructive text-xs px-1" title="Delete chatroom">×</button>
        </div>
      </div>
      {isExpanded && isActive && (
        <div className="ml-4 space-y-0.5 mt-0.5">
          {chats.map((chat) => (
            <div
              key={chat.id}
              onClick={() => onSelectChat(chat.id)}
              className={`group flex items-center justify-between px-2 py-1 rounded-md cursor-pointer text-xs ${
                activeChatId === chat.id
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
              }`}
            >
              <span className="truncate">{chat.name}</span>
              <button
                onClick={(e) => onDeleteChat(chat.id, e)}
                className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive px-1"
              >×</button>
            </div>
          ))}
          {chats.length === 0 && (
            <div className="text-[10px] text-muted-foreground px-2 py-1 italic">No chats yet</div>
          )}
        </div>
      )}
    </div>
  );
}
