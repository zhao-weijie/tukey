import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { Separator } from "@/components/ui/separator";
import { apiClient } from "@/lib/api";
import type { ModelConfig as MC, Provider } from "@/stores/chatStore";

interface Caps {
  supports_reasoning: boolean;
  supports_vision: boolean;
  max_tokens: number | null;
  max_input_tokens: number | null;
}

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
  const [caps, setCaps] = useState<Record<string, Caps>>({});

  const fetchCaps = useCallback(async (modelId: string) => {
    if (caps[modelId]) return;
    try {
      const c = await apiClient.getModelCapabilities(modelId);
      setCaps((prev) => ({ ...prev, [modelId]: c }));
    } catch {
      setCaps((prev) => ({
        ...prev,
        [modelId]: { supports_reasoning: false, supports_vision: false, max_tokens: null, max_input_tokens: null },
      }));
    }
  }, [caps]);

  useEffect(() => {
    models.forEach((m) => fetchCaps(m.model_id));
  }, [models.map((m) => m.model_id).join(",")]);

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

  const applyToAll = (sourceIdx: number, field: keyof MC | "reasoning_effort") => {
    const src = models[sourceIdx];
    const next = models.map((m, i) => {
      if (i === sourceIdx) return m;
      if (field === "reasoning_effort") {
        const val = src.extra_params.reasoning_effort;
        return { ...m, extra_params: { ...m.extra_params, reasoning_effort: val } };
      }
      return { ...m, [field]: src[field as keyof MC] };
    });
    onUpdate(next);
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

      {models.map((m, i) => {
        const mc = caps[m.model_id];
        const reasoning = mc?.supports_reasoning ?? false;
        return (
          <ModelCard key={m.id} model={m} idx={i} reasoning={reasoning}
            showApply={models.length > 1}
            onUpdate={updateModel} onRemove={removeModel} onApplyToAll={applyToAll} />
        );
      })}
    </div>
  );
}

/* ── per-model card ── */

interface CardProps {
  model: MC;
  idx: number;
  reasoning: boolean;
  showApply: boolean;
  onUpdate: (idx: number, patch: Partial<MC>) => void;
  onRemove: (idx: number) => void;
  onApplyToAll: (idx: number, field: keyof MC | "reasoning_effort") => void;
}

function ApplyBtn({ onClick }: { onClick: () => void }) {
  return (
    <button onClick={onClick} className="text-[10px] text-muted-foreground hover:text-foreground ml-1" title="Apply to all models">
      ⤵ all
    </button>
  );
}

function ModelCard({ model: m, idx, reasoning, showApply, onUpdate, onRemove, onApplyToAll }: CardProps) {
  const re = (m.extra_params.reasoning_effort as string) || "none";

  return (
    <div className="p-3 border border-border rounded-md space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{m.display_name}</span>
        <button onClick={() => onRemove(idx)} className="text-xs text-muted-foreground hover:text-destructive">×</button>
      </div>

      {/* System Prompt */}
      <div>
        <div className="flex items-center">
          <Label className="text-xs">System Prompt</Label>
          {showApply && <ApplyBtn onClick={() => onApplyToAll(idx, "system_prompt")} />}
        </div>
        <Textarea value={m.system_prompt} rows={2}
          onChange={(e) => onUpdate(idx, { system_prompt: e.target.value })}
          className="text-xs mt-1" placeholder="You are a helpful assistant..." />
      </div>

      {/* Temperature */}
      <div>
        <div className="flex items-center">
          <Label className="text-xs">Temperature: {m.temperature.toFixed(2)}</Label>
          {showApply && <ApplyBtn onClick={() => onApplyToAll(idx, "temperature")} />}
        </div>
        <Slider value={[m.temperature]} min={0} max={2} step={0.05}
          onValueChange={(v) => onUpdate(idx, { temperature: Array.isArray(v) ? v[0] : v })} className="mt-1" />
      </div>

      {/* Max Tokens */}
      <div>
        <div className="flex items-center">
          <Label className="text-xs">Max Tokens</Label>
          {showApply && <ApplyBtn onClick={() => onApplyToAll(idx, "max_tokens")} />}
        </div>
        <Input type="number" min={1}
          value={m.max_tokens ?? ""}
          onChange={(e) => onUpdate(idx, { max_tokens: e.target.value ? Number(e.target.value) : null })}
          placeholder="No limit" className="h-7 text-xs mt-1" />
      </div>

      {/* Top P */}
      <div>
        <div className="flex items-center">
          <Label className="text-xs">Top P: {m.top_p != null ? m.top_p.toFixed(2) : "default"}</Label>
          {showApply && <ApplyBtn onClick={() => onApplyToAll(idx, "top_p")} />}
        </div>
        <Slider value={[m.top_p ?? 1]} min={0} max={1} step={0.05}
          onValueChange={(v) => {
            const val = Array.isArray(v) ? v[0] : v;
            onUpdate(idx, { top_p: val === 1 ? null : val });
          }} className="mt-1" />
      </div>

      {/* Reasoning Effort — conditional */}
      {reasoning && (
        <div>
          <div className="flex items-center">
            <Label className="text-xs">Reasoning Effort</Label>
            {showApply && <ApplyBtn onClick={() => onApplyToAll(idx, "reasoning_effort")} />}
          </div>
          <select value={re}
            onChange={(e) => onUpdate(idx, { extra_params: { ...m.extra_params, reasoning_effort: e.target.value === "none" ? undefined : e.target.value } })}
            className="w-full mt-1 h-7 px-2 text-xs border border-input rounded-md bg-background">
            <option value="none">None</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
      )}

      <Separator />
    </div>
  );
}
