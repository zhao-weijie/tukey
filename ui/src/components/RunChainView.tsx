import { useEffect, useMemo, useState } from "react";
import { ArrowDown, Play, RefreshCw, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { ResponseCarousel } from "@/components/ResponseCarousel";
import { ConfigSetEditor } from "@/components/ConfigSetEditor";
import { RunOutputCard } from "@/components/RunOutputCard";
import { apiClient } from "@/lib/api";
import { contentText, useTukeyStore, type ConfigSet, type ConfigSlot, type Run } from "@/stores/tukeyStore";

interface Props {
  demoPrompt?: string | null;
  onDemoPromptUsed?: () => void;
}

export function RunChainView({ demoPrompt, onDemoPromptUsed }: Props) {
  const { activeDetail, loadChainDetail, loadWorkspace } = useTukeyStore();
  const [input, setInput] = useState(demoPrompt || "");
  const [completionCount, setCompletionCount] = useState(1);
  const [running, setRunning] = useState(false);
  const [showConfig, setShowConfig] = useState(false);

  useEffect(() => {
    if (demoPrompt) {
      setInput(demoPrompt);
      onDemoPromptUsed?.();
    }
  }, [demoPrompt, onDemoPromptUsed]);

  const chain = activeDetail?.chain;
  const configSet = useMemo(() => {
    if (!activeDetail) return null;
    return activeDetail.config_sets.find((item) => item.id === chain?.default_config_set_id)
      || activeDetail.config_sets[0]
      || null;
  }, [activeDetail, chain?.default_config_set_id]);
  const slots = configSet ? activeDetail?.config_slots[configSet.id] || [] : [];

  const runs = useMemo(() => {
    if (!activeDetail) return [];
    return [...activeDetail.runs].sort((a, b) => a.created_at.localeCompare(b.created_at));
  }, [activeDetail]);

  async function refresh() {
    await loadWorkspace();
    await loadChainDetail();
  }

  async function send() {
    const text = input.trim();
    if (!text || !chain || !configSet || running) return;
    setInput("");
    setRunning(true);
    try {
      const parent = runs[runs.length - 1];
      const run = await apiClient.createRun({
        name: text.slice(0, 80),
        status: "queued",
        kind: "interactive",
        config_set_id: configSet.id,
        task_id: undefined,
        chain_id: chain.id,
        parent_run_ids: parent ? [parent.id] : [],
      });
      if (!chain.root_run_id) {
        await apiClient.updateRunChain(chain.id, { root_run_id: run.id });
      }
      if (parent) {
        await apiClient.createRunChainEdge(chain.id, {
          parent_run_id: parent.id,
          child_run_id: run.id,
          mapping: {},
        });
      }
      await apiClient.executeRun(run.id, {
        n: completionCount,
        created_by: "user",
        inputs: [{ role: "user", content: [{ type: "text", text }] }],
      });
      await loadChainDetail(chain.id);
      await loadWorkspace();
    } finally {
      setRunning(false);
    }
  }

  if (!activeDetail || !chain) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
        Select or create a run chain to start comparing configurations
      </div>
    );
  }

  return (
    <div className="flex h-full min-w-0 flex-1 flex-col overflow-hidden">
      <div className="flex shrink-0 items-center justify-between gap-3 border-b border-border px-4 py-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium">{chain.name}</div>
          <div className="truncate text-xs text-muted-foreground">
            {configSet?.name || "No config set"} · {runs.length} run{runs.length === 1 ? "" : "s"}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" className="h-8 gap-1.5" onClick={refresh}>
            <RefreshCw size={14} /> Refresh
          </Button>
          <Button size="sm" variant={showConfig ? "secondary" : "outline"} className="h-8 gap-1.5" onClick={() => setShowConfig((v) => !v)}>
            <Settings size={14} /> Config
          </Button>
        </div>
      </div>

      {showConfig ? (
        <ConfigSetEditor
          configSet={configSet as ConfigSet | null}
          slots={slots}
          onChanged={async () => {
            await loadWorkspace();
            await loadChainDetail(chain.id);
          }}
        />
      ) : (
        <div className="flex-1 min-h-0 min-w-0 overflow-auto px-4 py-4">
          <div className="mx-auto max-w-6xl space-y-6">
            {runs.length === 0 && (
              <div className="flex min-h-64 items-center justify-center rounded-md border border-dashed border-border text-sm text-muted-foreground">
                Start this chain with a prompt
              </div>
            )}
            {runs.map((run, index) => (
              <RunBlock
                key={run.id}
                run={run}
                slots={slots}
                isLast={index === runs.length - 1}
                onChanged={() => loadChainDetail(chain.id)}
              />
            ))}
          </div>
        </div>
      )}

      <Separator />
      <div className="shrink-0 p-3">
        <div className="flex min-w-0 items-end gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder="Run a prompt across this config set..."
            rows={2}
            className="resize-none text-sm"
          />
          <div className="flex shrink-0 flex-col gap-1">
            <Input
              type="number"
              min={1}
              max={9}
              value={completionCount}
              onChange={(e) => setCompletionCount(Math.min(9, Math.max(1, Number(e.target.value) || 1)))}
              title="Completions per slot"
              className="h-8 w-16 text-center text-xs"
            />
            <Button onClick={send} disabled={running || !input.trim() || !configSet} className="h-9 gap-1.5">
              <Play size={14} /> {running ? "Running" : "Run"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function RunBlock({
  run,
  slots,
  isLast,
  onChanged,
}: {
  run: Run;
  slots: ConfigSlot[];
  isLast: boolean;
  onChanged: () => Promise<void>;
}) {
  const detail = useTukeyStore((s) => s.activeDetail);
  const inputs = detail?.inputs[run.id] || [];
  const outputs = detail?.outputs[run.id] || [];
  const annotations = detail?.annotations[run.id] || [];
  const slotById = Object.fromEntries(slots.map((slot) => [slot.id, slot]));
  const prompt = inputs.map((item) => contentText(item.content)).join("\n\n");
  const sortedOutputs = [...outputs].sort((a, b) =>
    `${a.slot_id}:${a.response_index}`.localeCompare(`${b.slot_id}:${b.response_index}`),
  );

  return (
    <div className="space-y-3">
      <div className="mx-auto max-w-3xl rounded-md bg-muted/35 px-4 py-3">
        <div className="mb-1 flex items-center justify-between text-xs text-muted-foreground">
          <span>Run {run.status}</span>
          <span>{new Date(run.created_at).toLocaleString()}</span>
        </div>
        <div className="whitespace-pre-wrap text-sm">{prompt || run.name || "No input recorded"}</div>
      </div>
      {outputs.length > 0 ? (
        <ResponseCarousel>
          {sortedOutputs.map((output) => (
            <RunOutputCard
              key={output.id}
              slot={slotById[output.slot_id]}
              output={output}
              annotations={annotations.filter((annotation) => annotation.target?.output_id === output.id)}
              onChanged={onChanged}
            />
          ))}
        </ResponseCarousel>
      ) : (
        <div className="rounded-md border border-border p-4 text-sm text-muted-foreground">
          {run.status === "running" || isLast ? "Waiting for outputs..." : "No outputs recorded"}
        </div>
      )}
      {!isLast && (
        <div className="flex justify-center text-muted-foreground">
          <ArrowDown size={16} />
        </div>
      )}
    </div>
  );
}
