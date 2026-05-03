import { useEffect, useState } from "react";
import { Plus, Trash, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { apiClient } from "@/lib/api";
import { useTukeyStore, type ConfigSet, type ConfigSlot } from "@/stores/tukeyStore";

interface Props {
  configSet: ConfigSet | null;
  slots: ConfigSlot[];
  onChanged: () => Promise<void>;
}

const emptySlot = {
  provider_id: "",
  provider_model_id: "",
  display_name: "",
  system_prompt: "",
  temperature: 1,
  max_tokens: null,
  top_p: null,
  extra_params: {},
  modality: "text",
  task_type: "chat_completion",
};

export function ConfigSetEditor({ configSet, slots, onChanged }: Props) {
  const { providers } = useTukeyStore();
  const [drafts, setDrafts] = useState<Record<string, Partial<ConfigSlot>>>({});
  const [newSlot, setNewSlot] = useState<any>(emptySlot);
  const [showAdd, setShowAdd] = useState(false);

  useEffect(() => {
    setDrafts(Object.fromEntries(slots.map((slot) => [slot.id, slot])));
  }, [slots]);

  if (!configSet) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Select a run chain to edit its config set
      </div>
    );
  }

  const orderedSlots = [...slots].sort((a, b) => {
    const ai = configSet.slot_order.indexOf(a.id);
    const bi = configSet.slot_order.indexOf(b.id);
    return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
  });

  async function saveSlot(slotId: string) {
    await apiClient.updateConfigSlot(configSet!.id, slotId, drafts[slotId]);
    await onChanged();
  }

  async function removeSlot(slotId: string) {
    if (!window.confirm("Disable this config slot for future runs? Existing run versions stay intact.")) return;
    await apiClient.deleteConfigSlot(configSet!.id, slotId);
    await onChanged();
  }

  async function addSlot() {
    if (!newSlot.provider_id || !newSlot.provider_model_id.trim()) return;
    await apiClient.createConfigSlot(configSet!.id, {
      ...newSlot,
      display_name: newSlot.display_name || newSlot.provider_model_id,
    });
    setNewSlot(emptySlot);
    setShowAdd(false);
    await onChanged();
  }

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden">
      <div className="flex shrink-0 items-center justify-between px-4 py-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium">{configSet.name}</div>
          <div className="text-xs text-muted-foreground">{orderedSlots.filter((s) => s.enabled).length} active slots</div>
        </div>
        <Button size="sm" variant="outline" onClick={() => setShowAdd((v) => !v)} className="h-8 gap-1.5">
          <Plus size={14} /> Slot
        </Button>
      </div>
      <Separator />
      <div className="flex-1 min-h-0 overflow-auto p-4">
        <div className="flex gap-3">
          {orderedSlots.map((slot) => {
            const draft = drafts[slot.id] || slot;
            return (
              <div key={slot.id} className="w-[300px] shrink-0 rounded-md border border-border p-3">
                <div className="mb-3 flex items-center justify-between gap-2">
                  <Input
                    value={draft.display_name || ""}
                    onChange={(e) => setDrafts((s) => ({ ...s, [slot.id]: { ...draft, display_name: e.target.value } }))}
                    className="h-8 text-sm font-medium"
                  />
                  <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => removeSlot(slot.id)} title="Disable slot">
                    <Trash size={14} />
                  </Button>
                </div>
                <SlotFields
                  value={draft}
                  onChange={(patch) => setDrafts((s) => ({ ...s, [slot.id]: { ...draft, ...patch } }))}
                />
                <Button size="sm" className="mt-3 h-8 w-full gap-1.5" onClick={() => saveSlot(slot.id)}>
                  <Save size={14} /> Save Slot
                </Button>
              </div>
            );
          })}
          {showAdd && (
            <div className="w-[300px] shrink-0 rounded-md border border-dashed border-border p-3">
              <div className="mb-3 text-sm font-medium">New Slot</div>
              <div className="space-y-3">
                <div>
                  <Label className="text-xs">Provider</Label>
                  <Select value={newSlot.provider_id} onValueChange={(provider_id) => setNewSlot((s: any) => ({ ...s, provider_id }))}>
                    <SelectTrigger className="mt-1 h-8 text-xs">
                      <SelectValue placeholder="Select provider" />
                    </SelectTrigger>
                    <SelectContent>
                      {providers.map((provider) => (
                        <SelectItem key={provider.id} value={provider.id}>{provider.display_name || provider.provider}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <SlotFields value={newSlot} onChange={(patch) => setNewSlot((s: any) => ({ ...s, ...patch }))} includeProvider={false} />
                <Button size="sm" className="h-8 w-full" onClick={addSlot}>Add Slot</Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SlotFields({
  value,
  onChange,
  includeProvider = true,
}: {
  value: Partial<ConfigSlot>;
  onChange: (patch: Partial<ConfigSlot>) => void;
  includeProvider?: boolean;
}) {
  const { providers } = useTukeyStore();
  return (
    <div className="space-y-3">
      {includeProvider && (
        <div>
          <Label className="text-xs">Provider</Label>
          <Select value={value.provider_id || ""} onValueChange={(provider_id) => onChange({ provider_id: provider_id || "" })}>
            <SelectTrigger className="mt-1 h-8 text-xs">
              <SelectValue placeholder="Select provider" />
            </SelectTrigger>
            <SelectContent>
              {providers.map((provider) => (
                <SelectItem key={provider.id} value={provider.id}>{provider.display_name || provider.provider}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
      <div>
        <Label className="text-xs">Model ID</Label>
        <Input
          value={value.provider_model_id || ""}
          onChange={(e) => onChange({ provider_model_id: e.target.value })}
          placeholder="openai/gpt-4o-mini"
          className="mt-1 h-8 text-xs"
        />
      </div>
      <div>
        <Label className="text-xs">Display Name</Label>
        <Input
          value={value.display_name || ""}
          onChange={(e) => onChange({ display_name: e.target.value })}
          className="mt-1 h-8 text-xs"
        />
      </div>
      <div>
        <Label className="text-xs">System Prompt</Label>
        <Textarea
          value={value.system_prompt || ""}
          onChange={(e) => onChange({ system_prompt: e.target.value })}
          rows={3}
          className="mt-1 text-xs"
        />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <Label className="text-xs">Temp</Label>
          <Input
            type="number"
            min={0}
            max={2}
            step={0.05}
            value={value.temperature ?? ""}
            onChange={(e) => onChange({ temperature: e.target.value === "" ? null : Number(e.target.value) })}
            className="mt-1 h-8 text-xs"
          />
        </div>
        <div>
          <Label className="text-xs">Max Tokens</Label>
          <Input
            type="number"
            value={value.max_tokens ?? ""}
            onChange={(e) => onChange({ max_tokens: e.target.value === "" ? null : Number(e.target.value) })}
            className="mt-1 h-8 text-xs"
          />
        </div>
      </div>
      <div>
        <Label className="text-xs">Task Type</Label>
        <Select value={value.task_type || "chat_completion"} onValueChange={(task_type) => onChange({ task_type: task_type || "chat_completion" })}>
          <SelectTrigger className="mt-1 h-8 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="chat_completion">Chat completion</SelectItem>
            <SelectItem value="image_generation">Image generation</SelectItem>
            <SelectItem value="image_edit">Image edit</SelectItem>
            <SelectItem value="embedding">Embedding</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
