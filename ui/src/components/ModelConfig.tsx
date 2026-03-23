import { useState, useEffect, useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { Separator } from "@/components/ui/separator";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
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
  const [availableModels, setAvailableModels] = useState<{ id: string; name: string }[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  const capsRef = useRef<Record<string, Caps>>({});

  const fetchCaps = useCallback(async (modelId: string) => {
    if (capsRef.current[modelId]) return;
    try {
      const c = await apiClient.getModelCapabilities(modelId);
      capsRef.current = { ...capsRef.current, [modelId]: c };
      setCaps({ ...capsRef.current });
    } catch {
      capsRef.current = {
        ...capsRef.current,
        [modelId]: { supports_reasoning: false, supports_vision: false, max_tokens: null, max_input_tokens: null },
      };
      setCaps({ ...capsRef.current });
    }
  }, []);

  useEffect(() => {
    models.forEach((m) => fetchCaps(m.model_id));
  }, [models.map((m) => m.model_id).join(",")]);

  // Fetch available models when provider changes
  useEffect(() => {
    if (!newProviderId) { setAvailableModels([]); return; }
    apiClient.getAvailableModels(newProviderId).then(setAvailableModels).catch(() => setAvailableModels([]));
  }, [newProviderId]);

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
      response_format: null,
      tools: null,
      tool_choice: null,
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
            <Select value={newProviderId} onValueChange={(v) => v && setNewProviderId(v)}>
              <SelectTrigger className="w-full mt-1 text-sm">
                <SelectValue placeholder="Select provider">
                  {providers.find((p) => p.id === newProviderId)?.display_name || providers.find((p) => p.id === newProviderId)?.provider || "Select provider"}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {providers.map((p) => (
                  <SelectItem key={p.id} value={p.id}>{p.display_name || p.provider}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="relative">
            <Label className="text-xs">Model ID</Label>
            <Input value={newModelId}
              onChange={(e) => { setNewModelId(e.target.value); setShowSuggestions(true); }}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
              placeholder="openai/gpt-5.2" className="h-8 text-sm mt-1" />
            {showSuggestions && availableModels.length > 0 && (
              <div className="absolute z-10 w-full mt-0.5 max-h-40 overflow-y-auto border border-input rounded-md bg-background shadow-md">
                {availableModels
                  .filter((m) => !newModelId || m.id.toLowerCase().includes(newModelId.toLowerCase()))
                  .slice(0, 20)
                  .map((m) => (
                    <button key={m.id} type="button"
                      className="w-full text-left px-2 py-1 text-xs hover:bg-accent truncate"
                      onMouseDown={(e) => { e.preventDefault(); setNewModelId(m.id); setShowSuggestions(false); }}>
                      {m.id}
                    </button>
                  ))}
              </div>
            )}
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

  // Local state + debounce for textareas to prevent cursor reset
  const [localPrompt, setLocalPrompt] = useState(m.system_prompt);
  const [localSchema, setLocalSchema] = useState(
    m.response_format?.type === "json_schema" ? JSON.stringify(m.response_format.json_schema || {}, null, 2) : ""
  );
  const [localTools, setLocalTools] = useState(m.tools ? JSON.stringify(m.tools, null, 2) : "");
  const promptDebounce = useRef<ReturnType<typeof setTimeout>>(undefined);
  const schemaDebounce = useRef<ReturnType<typeof setTimeout>>(undefined);
  const toolsDebounce = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Sync from parent (e.g. "Apply to all")
  useEffect(() => { setLocalPrompt(m.system_prompt); }, [m.system_prompt]);
  useEffect(() => {
    if (m.response_format?.type === "json_schema") {
      setLocalSchema(JSON.stringify(m.response_format.json_schema || {}, null, 2));
    }
  }, [m.response_format]);
  useEffect(() => {
    setLocalTools(m.tools ? JSON.stringify(m.tools, null, 2) : "");
  }, [m.tools]);

  // Cleanup on unmount
  useEffect(() => () => {
    clearTimeout(promptDebounce.current);
    clearTimeout(schemaDebounce.current);
    clearTimeout(toolsDebounce.current);
  }, []);

  const handlePromptChange = (value: string) => {
    setLocalPrompt(value);
    clearTimeout(promptDebounce.current);
    promptDebounce.current = setTimeout(() => onUpdate(idx, { system_prompt: value }), 500);
  };

  const handleSchemaChange = (value: string) => {
    setLocalSchema(value);
    clearTimeout(schemaDebounce.current);
    schemaDebounce.current = setTimeout(() => {
      try {
        const schema = JSON.parse(value);
        onUpdate(idx, { response_format: { type: "json_schema", json_schema: schema } });
      } catch { /* ignore parse errors while typing */ }
    }, 500);
  };

  const handleToolsChange = (value: string) => {
    setLocalTools(value);
    clearTimeout(toolsDebounce.current);
    toolsDebounce.current = setTimeout(() => {
      if (!value.trim()) { onUpdate(idx, { tools: null }); return; }
      try {
        const tools = JSON.parse(value);
        if (Array.isArray(tools)) onUpdate(idx, { tools });
      } catch { /* ignore parse errors while typing */ }
    }, 500);
  };

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
        <Textarea value={localPrompt} rows={2}
          onChange={(e) => handlePromptChange(e.target.value)}
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
          <Select value={re} onValueChange={(v) => onUpdate(idx, { extra_params: { ...m.extra_params, reasoning_effort: v === "none" ? undefined : v } })}>
            <SelectTrigger size="sm" className="w-full mt-1 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">None</SelectItem>
              <SelectItem value="low">Low</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="high">High</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Response Format */}
      <div>
        <div className="flex items-center">
          <Label className="text-xs">Response Format</Label>
        </div>
        <Select value={m.response_format?.type || "text"} onValueChange={(v) => {
            if (v === "text") onUpdate(idx, { response_format: null });
            else if (v === "json_object") onUpdate(idx, { response_format: { type: "json_object" } });
            else if (v === "json_schema") onUpdate(idx, { response_format: { type: "json_schema", json_schema: m.response_format?.json_schema || {} } });
          }}>
          <SelectTrigger size="sm" className="w-full mt-1 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="text">Text</SelectItem>
            <SelectItem value="json_object">JSON Object</SelectItem>
            <SelectItem value="json_schema">JSON Schema</SelectItem>
          </SelectContent>
        </Select>
        {m.response_format?.type === "json_schema" && (
          <Textarea
            value={localSchema}
            rows={3}
            onChange={(e) => handleSchemaChange(e.target.value)}
            className="text-xs mt-1 font-mono"
            placeholder='{"name": "my_schema", "schema": {...}}'
          />
        )}
      </div>

      {/* Tool Choice */}
      <div>
        <div className="flex items-center">
          <Label className="text-xs">Tool Choice</Label>
        </div>
        <Select value={typeof m.tool_choice === "string" ? m.tool_choice : m.tool_choice ? "function" : "none"} onValueChange={(v) => {
            if (v === "none") onUpdate(idx, { tool_choice: null });
            else onUpdate(idx, { tool_choice: v });
          }}>
          <SelectTrigger size="sm" className="w-full mt-1 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">None</SelectItem>
            <SelectItem value="auto">Auto</SelectItem>
            <SelectItem value="required">Required</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Tools */}
      <div>
        <div className="flex items-center">
          <Label className="text-xs">Tools (JSON)</Label>
        </div>
        <Textarea
          value={localTools}
          rows={3}
          onChange={(e) => handleToolsChange(e.target.value)}
          className="text-xs mt-1 font-mono"
          placeholder='[{"type": "function", "function": {"name": "...", "parameters": {...}}}]'
        />
      </div>

      <Separator />
    </div>
  );
}
