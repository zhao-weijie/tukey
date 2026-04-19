import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { GearSix } from "@phosphor-icons/react";
import { apiClient } from "@/lib/api";
import type { Provider } from "@/stores/chatStore";

interface Props {
  providers: Provider[];
  onUpdate: (providers: Provider[]) => void;
  externalOpen?: boolean;
  onExternalOpenChange?: (open: boolean) => void;
}

export function ProviderSetup({ providers, onUpdate, externalOpen, onExternalOpenChange }: Props) {
  const [internalOpen, setInternalOpen] = useState(false);
  const open = externalOpen ?? internalOpen;
  const setOpen = (v: boolean) => {
    onExternalOpenChange?.(v);
    setInternalOpen(v);
  };
  const [provider, setProvider] = useState("openai");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [stripModelPrefix, setStripModelPrefix] = useState(false);

  // Edit state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editApiKey, setEditApiKey] = useState("");
  const [editBaseUrl, setEditBaseUrl] = useState("");
  const [editDisplayName, setEditDisplayName] = useState("");

  const startEdit = (p: Provider) => {
    setEditingId(p.id);
    setEditApiKey("");
    setEditBaseUrl(p.base_url || "");
    setEditDisplayName(p.display_name || "");
  };

  const saveEdit = async (id: string) => {
    const updates: Record<string, any> = {};
    if (editApiKey.trim()) updates.api_key = editApiKey.trim();
    if (editDisplayName.trim()) updates.display_name = editDisplayName.trim();
    updates.base_url = editBaseUrl.trim() || null;
    const updated = await apiClient.updateProvider(id, updates);
    onUpdate(providers.map((p) => (p.id === id ? updated : p)));
    setEditingId(null);
  };

  const addProvider = async () => {
    if (!apiKey.trim()) return;
    const p = await apiClient.createProvider({
      provider: provider.trim(),
      api_key: apiKey.trim(),
      base_url: baseUrl.trim() || null,
      display_name: displayName.trim() || provider.trim(),
      strip_model_prefix: stripModelPrefix,
    });
    onUpdate([...providers, p]);
    setApiKey("");
    setBaseUrl("");
    setDisplayName("");
    setStripModelPrefix(false);
  };

  const removeProvider = async (id: string) => {
    if (!window.confirm("Removing a provider will break any model configurations that use it. Continue?")) return;
    await apiClient.deleteProvider(id);
    onUpdate(providers.filter((p) => p.id !== id));
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button size="sm" variant="outline" className="w-full h-7 text-xs gap-1.5" />}>
          <GearSix size={14} />
          Providers ({providers.length})
      </DialogTrigger>

      <DialogContent>
        <DialogHeader>
          <DialogTitle>API Providers</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {providers.map((p) => (
            <div key={p.id} className="p-2 border rounded-md text-sm space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">{p.display_name || p.provider}</div>
                  <div className="text-xs text-muted-foreground">
                    {p.base_url || "default"} &middot; {p.api_key.slice(0, 8)}...
                    {p.strip_model_prefix && <span className="ml-1 text-amber-500">&middot; strip prefix</span>}
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <TestButton providerId={p.id} />
                  <button onClick={() => startEdit(p)}
                    className="text-xs text-muted-foreground hover:text-foreground px-2">
                    Edit
                  </button>
                  <button onClick={() => removeProvider(p.id)}
                    className="text-xs text-muted-foreground hover:text-destructive px-2">
                    Remove
                  </button>
                </div>
              </div>
              {editingId === p.id && (
                <div className="space-y-2 pt-2 border-t">
                  <div>
                    <Label className="text-xs">New API Key (leave blank to keep current)</Label>
                    <Input value={editApiKey} onChange={(e) => setEditApiKey(e.target.value)}
                      type="password" placeholder="sk-..." className="h-8 text-sm mt-1" />
                  </div>
                  <div>
                    <Label className="text-xs">Base URL</Label>
                    <Input value={editBaseUrl} onChange={(e) => setEditBaseUrl(e.target.value)}
                      placeholder="https://api.openai.com/v1" className="h-8 text-sm mt-1" />
                  </div>
                  <div>
                    <Label className="text-xs">Display Name</Label>
                    <Input value={editDisplayName} onChange={(e) => setEditDisplayName(e.target.value)}
                      className="h-8 text-sm mt-1" />
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => saveEdit(p.id)} className="h-7 text-xs">
                      Save
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setEditingId(null)} className="h-7 text-xs">
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ))}

          <div className="space-y-2 pt-2 border-t">
            <div>
              <Label className="text-xs">Provider Type</Label>
              <Input value={provider} onChange={(e) => setProvider(e.target.value)}
                placeholder="openai" className="h-8 text-sm mt-1" />
            </div>
            <div>
              <Label className="text-xs">API Key</Label>
              <Input value={apiKey} onChange={(e) => setApiKey(e.target.value)}
                type="password" placeholder="sk-..." className="h-8 text-sm mt-1" />
            </div>
            <div>
              <Label className="text-xs">Base URL (optional)</Label>
              <Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://api.openai.com/v1" className="h-8 text-sm mt-1" />
            </div>
            <div>
              <Label className="text-xs">Display Name</Label>
              <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)}
                placeholder="My OpenAI" className="h-8 text-sm mt-1" />
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={stripModelPrefix}
                onChange={(e) => setStripModelPrefix(e.target.checked)}
                className="rounded border-input" />
              <span className="text-xs text-muted-foreground">Strip model prefix (e.g. openai/gpt-4o → gpt-4o)</span>
            </label>
            <Button size="sm" onClick={addProvider} className="w-full h-8">
              Add Provider
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function TestButton({ providerId }: { providerId: string }) {
  const [status, setStatus] = useState<"idle" | "testing" | "ok" | "fail">("idle");
  const [error, setError] = useState("");

  const test = async () => {
    setStatus("testing");
    setError("");
    try {
      const res = await apiClient.testProvider(providerId);
      if (res.ok) {
        setStatus("ok");
      } else {
        setStatus("fail");
        setError(res.error || "Unknown error");
      }
    } catch (e: any) {
      setStatus("fail");
      setError(e.message);
    }
  };

  return (
    <button onClick={test} disabled={status === "testing"}
      className="text-xs px-2 text-muted-foreground hover:text-foreground"
      title={error || undefined}>
      {status === "idle" && "Test"}
      {status === "testing" && "..."}
      {status === "ok" && "\u2713 OK"}
      {status === "fail" && "\u2717 Fail"}
    </button>
  );
}
