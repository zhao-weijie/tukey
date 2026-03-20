import { useState } from "react";
import { ChartBar, CaretLeft, CaretRight } from "@phosphor-icons/react";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { CopyButton } from "./CopyButton";
import { MarkdownContent } from "./MarkdownContent";
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

function formatCost(cost: number | null | undefined): string | null {
  if (cost === null || cost === undefined) return null;
  if (cost < 0.001) return `$${cost.toFixed(6)}`;
  return `$${cost.toFixed(3)}`;
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

  const active = responses[activeIndex];
  const content = streaming ? (streamingContent ?? "") : (active?.content ?? "");
  const error = active?.error;
  const metadata = streaming ? undefined : active;
  const err = error ? friendlyError(content) : null;

  const inlineStats: string[] = [];
  if (metadata) {
    const costStr = formatCost(metadata.cost);
    if (costStr) inlineStats.push(costStr);
    if (metadata.duration_ms != null) inlineStats.push(`${(metadata.duration_ms / 1000).toFixed(1)}s`);
    if (metadata.tokens_out != null) inlineStats.push(`${metadata.tokens_out} out`);
  }

  return (
    <div className="min-w-0 border border-border rounded-lg flex flex-col overflow-hidden h-full">
      {/* Scrollable area: sticky header + content */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="sticky top-0 z-10 flex items-center justify-between px-3 py-2 border-b border-border bg-muted/95 backdrop-blur-sm min-w-0 overflow-hidden">
          <span className="font-medium text-sm truncate" title={modelName}>{modelName}</span>
          {streaming && (
            <Badge variant="secondary" className="text-xs animate-pulse">
              {streamingTotal && streamingTotal > 1
                ? `streaming 1/${streamingTotal}...`
                : "streaming..."}
            </Badge>
          )}
        </div>
        <div className="p-3">
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
            <MarkdownContent content={content || (streaming ? "" : "No response")} />
          )}
        </div>
      </div>

      {/* Action bar: outside scroll container so it aligns across cards */}
      {!streaming && (content || responses.length > 1 || metadata) && (
        <div className="flex items-center justify-between px-2 py-1 border-t border-border bg-background">
          <div className="flex items-center gap-2">
            {metadata && (
              <Tooltip>
                <TooltipTrigger className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
                  <ChartBar size={14} />
                </TooltipTrigger>
                <TooltipContent side="top" align="end">
                  {[
                    metadata.tokens_in != null ? `${metadata.tokens_in} in` : null,
                    metadata.tokens_out != null ? `${metadata.tokens_out} out` : null,
                    metadata.duration_ms != null ? `${(metadata.duration_ms / 1000).toFixed(1)}s` : null,
                    metadata.tokens_per_sec != null ? `${metadata.tokens_per_sec} tok/s` : null,
                    metadata.cost === null || metadata.cost === undefined ? "cost: N/A" : `$${metadata.cost.toFixed(6)}`,
                  ].filter(Boolean).join(" · ")}
                </TooltipContent>
              </Tooltip>
            )}
            {inlineStats.length > 0 && (
              <span className="text-xs text-muted-foreground">
                {inlineStats.join(" · ")}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            {responses.length > 1 && (
              <>
                <button
                  onClick={() => onIndexChange(Math.max(0, activeIndex - 1))}
                  disabled={activeIndex === 0}
                  className="p-0.5 rounded hover:bg-muted disabled:opacity-30 disabled:cursor-default"
                >
                  <CaretLeft size={14} />
                </button>
                <span className="text-xs text-muted-foreground tabular-nums">
                  {activeIndex + 1}/{responses.length}
                </span>
                <button
                  onClick={() => onIndexChange(Math.min(responses.length - 1, activeIndex + 1))}
                  disabled={activeIndex === responses.length - 1}
                  className="p-0.5 rounded hover:bg-muted disabled:opacity-30 disabled:cursor-default"
                >
                  <CaretRight size={14} />
                </button>
              </>
            )}
            {!error && content && <CopyButton text={content} size={14} />}
          </div>
        </div>
      )}
    </div>
  );
}
