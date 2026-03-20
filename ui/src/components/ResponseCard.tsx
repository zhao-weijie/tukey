import { useState } from "react";
import { ChartBar, CaretLeft, CaretRight } from "@phosphor-icons/react";
import { Badge } from "@/components/ui/badge";
import type { ResponseMeta } from "@/stores/chatStore";

interface Props {
  modelName: string;
  responses: ResponseMeta[];
  activeIndex: number;
  onIndexChange: (index: number) => void;
  streaming?: boolean;
  streamingContent?: string;
  streamingTotal?: number;
}

function friendlyError(raw: string): { summary: string; full: string } {
  const lines = raw.trim().split("\n");
  const last = lines[lines.length - 1].trim();
  return { summary: last || raw, full: raw };
}

export function ResponseCard({
  modelName,
  responses,
  activeIndex,
  onIndexChange,
  streaming,
  streamingContent,
  streamingTotal,
}: Props) {
  const [showDetails, setShowDetails] = useState(false);
  const [showMeta, setShowMeta] = useState(false);

  const active = responses[activeIndex];
  const content = streaming ? (streamingContent ?? "") : (active?.content ?? "");
  const error = active?.error;
  const metadata = streaming ? undefined : active;
  const err = error ? friendlyError(content) : null;

  return (
    <div className="min-w-0 border border-border rounded-lg flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-muted/30 min-w-0 overflow-hidden">
        <span className="font-medium text-sm truncate" title={modelName}>{modelName}</span>
        {streaming && (
          <Badge variant="secondary" className="text-xs animate-pulse">
            {streamingTotal && streamingTotal > 1
              ? `streaming 1/${streamingTotal}...`
              : "streaming..."}
          </Badge>
        )}
      </div>
      <div className="flex-1 p-3 overflow-auto">
        {err ? (
          <div className="rounded-md border border-destructive/40 bg-destructive/5 p-3 space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-destructive uppercase">Error</span>
            </div>
            <p className="text-sm text-destructive">{err.summary}</p>
            {err.full !== err.summary && (
              <>
                <button
                  onClick={() => setShowDetails(!showDetails)}
                  className="text-xs text-muted-foreground hover:text-foreground underline"
                >
                  {showDetails ? "Hide details" : "Show details"}
                </button>
                {showDetails && (
                  <pre className="whitespace-pre-wrap text-xs text-muted-foreground mt-1 max-h-48 overflow-auto">
                    {err.full}
                  </pre>
                )}
              </>
            )}
          </div>
        ) : (
          <pre className="whitespace-pre-wrap text-sm font-sans">
            {content || (streaming ? "" : "No response")}
          </pre>
        )}
      </div>
      {/* Cycling UI */}
      {responses.length > 1 && !streaming && (
        <div className="flex items-center justify-center gap-2 px-3 py-1.5 border-t border-border">
          <button
            onClick={() => onIndexChange(Math.max(0, activeIndex - 1))}
            disabled={activeIndex === 0}
            className="p-0.5 rounded hover:bg-muted disabled:opacity-30 disabled:cursor-default"
          >
            <CaretLeft size={14} />
          </button>
          <span className="text-xs text-muted-foreground tabular-nums">
            {activeIndex + 1} / {responses.length}
          </span>
          <button
            onClick={() => onIndexChange(Math.min(responses.length - 1, activeIndex + 1))}
            disabled={activeIndex === responses.length - 1}
            className="p-0.5 rounded hover:bg-muted disabled:opacity-30 disabled:cursor-default"
          >
            <CaretRight size={14} />
          </button>
        </div>
      )}
      {metadata && !streaming && (
        <div className="border-t border-border">
          <button
            onClick={() => setShowMeta(!showMeta)}
            className="flex items-center gap-1 px-3 py-1.5 text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Toggle metadata"
          >
            <ChartBar size={16} weight={showMeta ? "fill" : "regular"} />
          </button>
          {showMeta && (
            <div className="flex flex-wrap gap-2 px-3 py-2 bg-muted/20 text-xs text-muted-foreground">
              {metadata.tokens_in != null && <span>{metadata.tokens_in} in</span>}
              {metadata.tokens_out != null && <span>{metadata.tokens_out} out</span>}
              {metadata.duration_ms != null && <span>{(metadata.duration_ms / 1000).toFixed(1)}s</span>}
              {metadata.tokens_per_sec != null && <span>{metadata.tokens_per_sec} tok/s</span>}
              {metadata.cost === null || metadata.cost === undefined
                ? <span>cost: N/A</span>
                : <span>${metadata.cost.toFixed(6)}</span>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
