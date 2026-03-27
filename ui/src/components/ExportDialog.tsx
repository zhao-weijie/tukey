import { useState, useEffect } from "react";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

interface Turn {
  id: string;
  content: string;
  created_at?: string;
  responses?: { model_id: string }[];
}

interface ExportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "chatroom" | "chat";
  chatroomId: string;
  chatId?: string | null;
  chatName?: string;
  chatroomName?: string;
}

function downloadJson(data: any, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function ExportDialog({
  open,
  onOpenChange,
  mode,
  chatroomId,
  chatId,
  chatName,
  chatroomName,
}: ExportDialogProps) {
  const [includeAnnotations, setIncludeAnnotations] = useState(true);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [selectedTurnIds, setSelectedTurnIds] = useState<Set<string>>(new Set());
  const [allSelected, setAllSelected] = useState(true);
  const [loading, setLoading] = useState(false);

  // Fetch turns when dialog opens in chat mode
  useEffect(() => {
    if (!open || mode !== "chat" || !chatId) {
      setTurns([]);
      return;
    }
    apiClient.getMessages(chatroomId, chatId).then((msgs) => {
      setTurns(msgs);
      setSelectedTurnIds(new Set(msgs.map((m: Turn) => m.id)));
      setAllSelected(true);
    });
  }, [open, mode, chatroomId, chatId]);

  const toggleTurn = (id: string) => {
    setSelectedTurnIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      setAllSelected(next.size === turns.length);
      return next;
    });
  };

  const toggleAll = () => {
    if (allSelected) {
      setSelectedTurnIds(new Set());
      setAllSelected(false);
    } else {
      setSelectedTurnIds(new Set(turns.map((t) => t.id)));
      setAllSelected(true);
    }
  };

  const handleExport = async () => {
    setLoading(true);
    try {
      if (mode === "chatroom") {
        const data = await apiClient.exportChatroom(chatroomId, {
          include_annotations: includeAnnotations,
        });
        const name = (chatroomName || chatroomId.slice(0, 8)).replace(/\s+/g, "_").toLowerCase();
        downloadJson(data, `tukey-${name}.json`);
      } else if (chatId) {
        const turnIds = allSelected ? undefined : Array.from(selectedTurnIds);
        const data = await apiClient.exportChat(chatroomId, chatId, {
          include_annotations: includeAnnotations,
          turn_ids: turnIds,
        });
        const name = (chatName || chatId.slice(0, 8)).replace(/\s+/g, "_").toLowerCase();
        downloadJson(data, `tukey-${name}.json`);
      }
      onOpenChange(false);
    } finally {
      setLoading(false);
    }
  };

  const canExport = mode === "chatroom" || selectedTurnIds.size > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            Export {mode === "chatroom" ? "Chatroom" : "Chat"}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Annotation toggle */}
          <div className="flex items-center gap-2">
            <Checkbox
              id="include-annotations"
              checked={includeAnnotations}
              onCheckedChange={(v) => setIncludeAnnotations(v === true)}
            />
            <Label htmlFor="include-annotations" className="text-sm cursor-pointer">
              Include annotations
            </Label>
          </div>

          {/* Turn selection (chat mode only) */}
          {mode === "chat" && turns.length > 0 && (
            <>
              <Separator />
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Select turns</span>
                  <button
                    onClick={toggleAll}
                    className="text-xs text-muted-foreground hover:text-foreground"
                  >
                    {allSelected ? "Deselect all" : "Select all"}
                  </button>
                </div>
                <ScrollArea className="max-h-60">
                  <div className="space-y-1 pr-3">
                    {turns.map((turn, i) => (
                      <div
                        key={turn.id}
                        className="flex items-start gap-2 py-1.5 px-1 rounded hover:bg-accent/50"
                      >
                        <Checkbox
                          id={`turn-${turn.id}`}
                          checked={selectedTurnIds.has(turn.id)}
                          onCheckedChange={() => toggleTurn(turn.id)}
                          className="mt-0.5"
                        />
                        <Label
                          htmlFor={`turn-${turn.id}`}
                          className="text-xs cursor-pointer leading-snug min-w-0"
                        >
                          <span className="text-muted-foreground mr-1">
                            {i + 1}.
                          </span>
                          <span className="line-clamp-2">
                            {turn.content}
                          </span>
                        </Label>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleExport} disabled={!canExport || loading}>
            {loading ? "Exporting..." : "Export"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
