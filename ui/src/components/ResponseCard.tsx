import { Badge } from "@/components/ui/badge";
import type { ResponseMeta } from "@/stores/chatStore";

interface Props {
  modelName: string;
  content: string;
  metadata?: Partial<ResponseMeta>;
  streaming?: boolean;
  error?: boolean;
}

export function ResponseCard({ modelName, content, metadata, streaming, error }: Props) {
  return (
    <div className="flex-1 min-w-0 border border-border rounded-lg flex flex-col">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-muted/30">
        <span className="font-medium text-sm truncate">{modelName}</span>
        {streaming && (
          <Badge variant="secondary" className="text-xs animate-pulse">
            streaming...
          </Badge>
        )}
      </div>
      <div className="flex-1 p-3 overflow-auto">
        <pre className={`whitespace-pre-wrap text-sm font-sans ${error ? "text-destructive" : ""}`}>
          {content || (streaming ? "" : "No response")}
        </pre>
      </div>
      {metadata && !streaming && (
        <div className="flex flex-wrap gap-2 px-3 py-2 border-t border-border bg-muted/20 text-xs text-muted-foreground">
          {metadata.tokens_in != null && (
            <span>{metadata.tokens_in} in</span>
          )}
          {metadata.tokens_out != null && (
            <span>{metadata.tokens_out} out</span>
          )}
          {metadata.duration_ms != null && (
            <span>{(metadata.duration_ms / 1000).toFixed(1)}s</span>
          )}
          {metadata.tokens_per_sec != null && (
            <span>{metadata.tokens_per_sec} tok/s</span>
          )}
          {metadata.cost != null && metadata.cost > 0 && (
            <span>${metadata.cost.toFixed(6)}</span>
          )}
        </div>
      )}
    </div>
  );
}
