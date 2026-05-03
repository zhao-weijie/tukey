import { useCallback, useEffect, useRef, useState } from "react";
import { Search } from "lucide-react";
import { apiClient } from "@/lib/api";
import { useTukeyStore } from "@/stores/tukeyStore";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";

interface SearchResult {
  type: string;
  chain_id?: string;
  chain_name?: string;
  task_name?: string;
  run_id?: string;
  match: string;
  snippet: string;
}

export function SearchDialog() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const { setActiveChainId, loadChainDetail } = useTukeyStore();

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
    timerRef.current = setTimeout(() => doSearch(query), 250);
    return () => clearTimeout(timerRef.current);
  }, [query, doSearch]);

  async function handleSelect(result: SearchResult) {
    if (result.chain_id) {
      setActiveChainId(result.chain_id);
      await loadChainDetail(result.chain_id);
    }
    setOpen(false);
    setQuery("");
    setResults([]);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button size="icon" variant="ghost" className="h-8 w-8" />}>
        <Search size={15} />
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Search</DialogTitle>
        </DialogHeader>
        <Input
          placeholder="Search tasks, chains, runs, outputs..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
          className="text-sm"
        />
        <ScrollArea className="max-h-72">
          <div className="space-y-1">
            {results.map((result, index) => (
              <button
                key={`${result.type}-${result.chain_id}-${result.run_id}-${index}`}
                onClick={() => handleSelect(result)}
                className="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent"
              >
                <div className="flex items-center gap-1.5">
                  <span className="shrink-0 text-[10px] uppercase text-muted-foreground">{result.type}</span>
                  <span className="truncate font-medium">
                    {result.chain_name || result.task_name || result.run_id || result.match}
                  </span>
                </div>
                <div className="mt-0.5 truncate text-xs text-muted-foreground">{result.snippet}</div>
              </button>
            ))}
            {query && results.length === 0 && (
              <div className="py-4 text-center text-xs text-muted-foreground">No results</div>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
