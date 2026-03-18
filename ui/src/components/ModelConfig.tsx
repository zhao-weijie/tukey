import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { Separator } from "@/components/ui/separator";
import type { ModelConfig as MC, Provider } from "@/stores/chatStore";

interface Props {
  models: MC[];
  providers: Provider[];
  onUpdate: (models: MC[]) => void;
}

export function ModelConfig({ models, providers, onUpdate }: Props) {
  const [showAdd, setShowAdd] = useState(false);
  const [newModelId, setNewModelId] = useState("");
  const [newProviderId, setNewProviderId] = useState(providers[0]?.id || "");
  const [newDisplayName, setNewDisplayName] = useState("");

  const addModel = () => {
    if (!newModelId.trim() || !newProviderId) return;
    const m: MC = {
      id: crypto.randomUUID(),
      provider_id: newProviderId,
      model_id: newModelId.trim(),
      display_name: newDisplayName.trim() || newModelId.trim(),
      system_prompt: "",
      temperature: 1.0,
      max_tokens: null,
      top_p: null,
      extra_params: {},
    };
    onUpdate([...models, m]);
    setNewModelId("");
    setNewDisplayName("");
    setShowAdd(false);
  };

  const updateModel = (idx: number, patch: Partial<MC>) => {
    const next = [...models];
    next[idx] = { ...next[idx], ...patch };
    onUpdate(next);
  };

  const removeModel = (idx: number) => {
    onUpdate(models.filter((_, i) => i !== idx));
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Models</span>
        <Button size="sm" variant="outline" onClick={() => setShowAdd(!showAdd)} className="h-7 text-xs">
          {showAdd ? "Cancel" : "+ Add Model"}
        </Button>
      </div>

      {showAdd && (
        <div className="space-y-2 p-3 border border-border rounded-md bg-muted/20">
          <div>
            <Label className="text-xs">Provider</Label>
            <select
              value={newProviderId}
              onChange={(e) => setNewProviderId(e.target.value)}
              className="w-full mt-1 h-8 px-2 text-sm border border-input rounded-md bg-background"
            >
              {providers.map((p) => (
                <option key={p.id} value={p.id}>{p.display_name || p.provider}</option>
              ))}
            </select>
          </div>
          <div>
            <Label className="text-xs">Model ID</Label>
            <Input value={newModelId} onChange={(e) => setNewModelId(e.target.value)}
              placeholder="openai/gpt-5.2" className="h-8 text-sm mt-1" />
            <p className="text-[10px] text-muted-foreground mt-1">
              Use openai/ prefix for gateway models (e.g. openai/claude-4.6-sonnet, openai/gemini-2.5-pro)
            </p>
          </div>
          <div>
            <Label className="text-xs">Display Name</Label>
            <Input value={newDisplayName} onChange={(e) => setNewDisplayName(e.target.value)}
              placeholder="GPT 5.2" className="h-8 text-sm mt-1" />
          </div>
          <Button size="sm" onClick={addModel} className="h-7 text-xs w-full">Add</Button>
        </div>
      )}

      {models.map((m, i) => (
        <div key={m.id} className="p-3 border border-border rounded-md space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{m.display_name}</span>
            <button onClick={() => removeModel(i)} className="text-xs text-muted-foreground hover:text-destructive">×</button>
          </div>
          <div>
            <Label className="text-xs">System Prompt</Label>
            <Textarea value={m.system_prompt} rows={2}
              onChange={(e) => updateModel(i, { system_prompt: e.target.value })}
              className="text-xs mt-1" placeholder="You are a helpful assistant..." />
          </div>
          <div>
            <Label className="text-xs">Temperature: {m.temperature.toFixed(2)}</Label>
            <Slider value={[m.temperature]} min={0} max={2} step={0.05}
              onValueChange={([v]) => updateModel(i, { temperature: v })} className="mt-1" />
          </div>
          <Separator />
        </div>
      ))}
    </div>
  );
}
