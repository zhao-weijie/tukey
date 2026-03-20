import { useState, useEffect, useRef, useCallback } from "react";
import { apiClient } from "@/lib/api";
import { useChatStore } from "@/stores/chatStore";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";

interface SearchResult {
  type: string;
  chatroom_id: string;
  chatroom_name: string;
  chat_id?: string;
  chat_name?: string;
  message_id?: string;
  match: string;
  snippet: string;
}

export function SearchDialog() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const { setActiveChatroom, setActiveChat } = useChatStore();

  // Cmd+K / Ctrl+K global shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen(true);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      return;
    }
    try {
      const res = await apiClient.search(q);
      setResults(res.results);
    } catch {
      setResults([]);
    }
  }, []);

  useEffect(() => {
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => doSearch(query), 300);
    return () => clearTimeout(timerRef.current);
  }, [query, doSearch]);

  const handleSelect = (r: SearchResult) => {
    setActiveChatroom(r.chatroom_id);
    if (r.chat_id) setActiveChat(r.chat_id);
    setOpen(false);
    setQuery("");
    setResults([]);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        className="text-xs text-muted-foreground hover:text-foreground px-2 py-1"
        render={<button />}
      >
        Search
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Search</DialogTitle>
        </DialogHeader>
        <Input
          placeholder="Search chatrooms, chats, messages..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
          className="text-sm"
        />
        <ScrollArea className="max-h-64">
          <div className="space-y-1">
            {results.map((r, i) => (
              <button
                key={`${r.type}-${r.chatroom_id}-${r.chat_id}-${r.message_id}-${i}`}
                onClick={() => handleSelect(r)}
                className="w-full text-left px-2 py-1.5 rounded-md hover:bg-accent text-sm"
              >
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] uppercase text-muted-foreground shrink-0">
                    {r.type}
                  </span>
                  <span className="font-medium truncate">
                    {r.chatroom_name}
                    {r.chat_name ? ` / ${r.chat_name}` : ""}
                  </span>
                </div>
                <div className="text-xs text-muted-foreground truncate mt-0.5">
                  {r.snippet}
                </div>
              </button>
            ))}
            {query && results.length === 0 && (
              <div className="text-xs text-muted-foreground text-center py-4">
                No results
              </div>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
