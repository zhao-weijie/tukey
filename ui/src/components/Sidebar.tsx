import { useEffect, useState, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { ProviderSetup } from "./ProviderSetup";
import { McpServerSetup } from "./McpServerSetup";
import { SearchDialog } from "./SearchDialog";
import { DataDirDialog } from "./DataDirDialog";
import {
  CaretLeft, CaretRight, CaretDown,
  Plus, X, DownloadSimple,
  FolderOpen,
} from "@phosphor-icons/react";
import { cn } from "@/lib/utils";
import type { Chatroom, Chat } from "@/stores/chatStore";

function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window !== "undefined" ? window.matchMedia(query).matches : false
  );
  useEffect(() => {
    const mql = window.matchMedia(query);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [query]);
  return matches;
}

interface SidebarProps {
  open: boolean;
  onToggle: () => void;
  providerDialogOpen?: boolean;
  onProviderDialogOpenChange?: (open: boolean) => void;
}

export function Sidebar({ open, onToggle, providerDialogOpen, onProviderDialogOpenChange }: SidebarProps) {
  const isSmallScreen = useMediaQuery("(max-width: 767px)");
  const {
    chatrooms, setChatrooms,
    activeChatroomId, setActiveChatroom,
    chats, setChats,
    activeChatId, setActiveChat,
    providers, setProviders,
    mcpServers, setMcpServers,
    setMessages,
  } = useChatStore();
  const [newName, setNewName] = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const importRef = useRef<HTMLInputElement>(null);
  const [dataDir, setDataDir] = useState("");
  const [dataDirDialogOpen, setDataDirDialogOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.listChatrooms().then(setChatrooms).catch(console.error).finally(() => setLoading(false));
    apiClient.listProviders().then(setProviders).catch(console.error);
    apiClient.listMcpServers().then(setMcpServers).catch(console.error);
    apiClient.getHealth().then((h) => setDataDir(h.data_dir)).catch(console.error);
  }, [setChatrooms, setProviders]);

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
    if (!window.confirm("Delete this chatroom and all its chats?")) return;
    await apiClient.deleteChatroom(id);
    setChatrooms(chatrooms.filter((r) => r.id !== id));
    if (activeChatroomId === id) {
      setActiveChatroom(null);
      setActiveChat(null);
      setMessages([]);
    }
  };

  const renameChatroom = async (id: string, name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    const updated = await apiClient.updateChatroom(id, { name: trimmed });
    setChatrooms(chatrooms.map((cr) => (cr.id === id ? updated : cr)));
  };

  const renameChat = async (chatroomId: string, chatId: string, name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    const updated = await apiClient.updateChat(chatroomId, chatId, { name: trimmed });
    setChats(chats.map((c) => (c.id === chatId ? updated : c)));
  };

  const toggleExpand = (id: string) => {
    setExpanded((e) => ({ ...e, [id]: !e[id] }));
  };

  const selectChatroom = (id: string) => {
    setActiveChatroom(id);
    setActiveChat(null);
    setExpanded((e) => ({ ...e, [id]: true }));
    if (isSmallScreen) onToggle();
  };

  const createChat = async (chatroomId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const chat = await apiClient.createChat(chatroomId);
    if (activeChatroomId === chatroomId) {
      setChats([...chats, chat]);
    } else {
      setActiveChatroom(chatroomId);
    }
    setActiveChat(chat.id);
    setExpanded((prev) => ({ ...prev, [chatroomId]: true }));
  };

  const deleteChat = async (chatroomId: string, chatId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm("Delete this chat?")) return;
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
    }
    setActiveChat(chatId);
    if (isSmallScreen) onToggle();
  };

  return (
    <>
    {/* Backdrop for small screens */}
    {isSmallScreen && open && (
      <div
        className="fixed inset-0 z-30 bg-black/40"
        onClick={onToggle}
      />
    )}
    <div className={cn(
      "border-r border-border flex flex-col h-full bg-sidebar transition-all duration-200",
      isSmallScreen
        ? cn("fixed inset-y-0 left-0 z-40 w-64", open ? "translate-x-0" : "-translate-x-full")
        : cn("relative", open ? "w-64" : "w-12")
    )}>
      {/* FAB toggle at right border */}
      <button
        onClick={onToggle}
        className={cn(
          "absolute top-4 z-20 w-5 h-5 rounded-full bg-sidebar border border-border shadow-sm flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent transition-colors",
          isSmallScreen ? "-right-6" : "-right-2.5"
        )}
        title={open ? "Collapse sidebar" : "Expand sidebar"}
      >
        {open ? <CaretLeft size={16} /> : <CaretRight size={16} />}
      </button>

      {!open && !isSmallScreen && (
        <div className="flex items-center justify-center p-3">
          <img src="/logos/tukey-light-none.svg" alt="Tukey" className="h-6 w-6" />
        </div>
      )}

      {(open || isSmallScreen) && (
      <>
      <div className="p-3 flex items-center justify-between">
        <img src="/logos/tukey-light-right.svg" alt="Tukey" className="h-8 w-auto" />
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
        <Button size="sm" onClick={createChatroom} className="h-8 px-2 shrink-0" title="New chatroom">
          <Plus size={16} />
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => importRef.current?.click()}
          className="h-8 px-2 shrink-0"
          title="Import chatroom"
        >
          <DownloadSimple size={16} />
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
          {loading && (
            <>
              <div className="h-8 rounded-md bg-muted/40 animate-pulse mx-1" />
              <div className="h-8 rounded-md bg-muted/40 animate-pulse mx-1" />
              <div className="h-8 rounded-md bg-muted/40 animate-pulse mx-1" />
            </>
          )}
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
              onRenameChatroom={(name) => renameChatroom(cr.id, name)}
              onRenameChat={(chatId, name) => renameChat(cr.id, chatId, name)}
            />
          ))}
        </div>
      </ScrollArea>
      <Separator />
      <div className="p-2 space-y-1.5">
        <ProviderSetup
          providers={providers}
          onUpdate={setProviders}
          externalOpen={providerDialogOpen}
          onExternalOpenChange={onProviderDialogOpenChange}
        />
        <McpServerSetup servers={mcpServers} onUpdate={setMcpServers} />
        {dataDir && (
          <div
            className="flex items-center gap-1.5 px-1 py-0.5 rounded-md text-[10px] text-muted-foreground hover:text-foreground hover:bg-accent/50 cursor-pointer transition-colors"
            title={dataDir}
            onClick={() => setDataDirDialogOpen(true)}
          >
            <FolderOpen size={12} className="shrink-0" />
            <span className="truncate">{dataDir}</span>
          </div>
        )}
      </div>
      </>
      )}
    </div>
    <DataDirDialog
      open={dataDirDialogOpen}
      onOpenChange={setDataDirDialogOpen}
      currentDir={dataDir}
      onSwitch={async (newDir) => {
        setDataDir(newDir);
        // Refresh all state after switching data directory
        const rooms = await apiClient.listChatrooms();
        setChatrooms(rooms);
        const provs = await apiClient.listProviders();
        setProviders(provs);
        setActiveChatroom(null);
        setActiveChat(null);
        setMessages([]);
        setChats([]);
      }}
    />
    </>
  );
}

/* ── Inline editable name ── */

function InlineEdit({ value, onSave }: { value: string; onSave: (v: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { if (editing) inputRef.current?.select(); }, [editing]);

  const commit = () => {
    setEditing(false);
    if (draft.trim() && draft.trim() !== value) onSave(draft.trim());
    else setDraft(value);
  };

  if (!editing) {
    return (
      <span
        className="truncate cursor-pointer"
        onDoubleClick={(e) => { e.stopPropagation(); setEditing(true); setDraft(value); }}
        title="Double-click to rename"
      >
        {value}
      </span>
    );
  }

  return (
    <input
      ref={inputRef}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") commit();
        if (e.key === "Escape") { setEditing(false); setDraft(value); }
      }}
      onClick={(e) => e.stopPropagation()}
      className="bg-transparent border-b border-foreground/30 outline-none text-sm w-full"
    />
  );
}

/* ── Chatroom tree item ── */

function ChatroomItem({
  chatroom, isActive, isExpanded, activeChatId, chats,
  onToggle, onSelect, onDelete, onExport, onCreateChat, onSelectChat, onDeleteChat,
  onRenameChatroom, onRenameChat,
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
  onRenameChatroom: (name: string) => void;
  onRenameChat: (chatId: string, name: string) => void;
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
        <div className="flex items-center gap-1.5 truncate min-w-0">
          <span className="text-muted-foreground shrink-0">
            {isExpanded ? <CaretDown size={12} /> : <CaretRight size={12} />}
          </span>
          <InlineEdit value={chatroom.name} onSave={onRenameChatroom} />
          <span className="text-[10px] text-muted-foreground ml-1 shrink-0">
            {chatroom.models?.length || 0}m
          </span>
        </div>
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 shrink-0">
          <button onClick={onCreateChat} className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground" title="New chat">
            <Plus size={14} />
          </button>
          <button onClick={onExport} className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground" title="Export">
            <DownloadSimple size={14} />
          </button>
          <button onClick={onDelete} className="p-1 rounded hover:bg-destructive/20 text-muted-foreground hover:text-destructive" title="Delete">
            <X size={14} />
          </button>
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
              <InlineEdit value={chat.name} onSave={(name) => onRenameChat(chat.id, name)} />
              <button
                onClick={(e) => onDeleteChat(chat.id, e)}
                className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-destructive/20 text-muted-foreground hover:text-destructive"
                title="Delete chat"
              >
                <X size={12} />
              </button>
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
