import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { apiClient } from "@/lib/api";

interface DataDirDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentDir: string;
  onSwitch: (newDir: string) => Promise<void>;
}

export function DataDirDialog({ open, onOpenChange, currentDir, onSwitch }: DataDirDialogProps) {
  const [newDir, setNewDir] = useState("");
  const [switching, setSwitching] = useState(false);
  const [error, setError] = useState("");

  const handleSwitch = async () => {
    const dir = newDir.trim();
    if (!dir) return;
    setSwitching(true);
    setError("");
    try {
      const res = await apiClient.setDataDir(dir);
      await onSwitch(res.data_dir);
      setNewDir("");
      onOpenChange(false);
    } catch (e: any) {
      setError(e.message || "Failed to switch directory");
    } finally {
      setSwitching(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Data Directory</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label className="text-xs text-muted-foreground">Current directory</Label>
            <p className="text-sm font-mono mt-1 break-all">{currentDir}</p>
          </div>
          <div>
            <Label className="text-xs">Switch to a new directory</Label>
            <Input
              value={newDir}
              onChange={(e) => setNewDir(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSwitch()}
              placeholder="C:\Users\you\.tukey-project"
              className="h-8 text-sm mt-1 font-mono"
            />
          </div>
          <p className="text-[11px] text-muted-foreground">
            Switching will load chatrooms and providers from the new directory. Active chats will be disconnected.
          </p>
          {error && (
            <p className="text-[11px] text-destructive">{error}</p>
          )}
          <Button
            size="sm"
            onClick={handleSwitch}
            disabled={!newDir.trim() || switching}
            className="w-full h-8"
          >
            {switching ? "Switching..." : "Switch Directory"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
