import { useState } from "react";
import { Check, Copy, MessageSquare, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { MarkdownContent } from "@/components/MarkdownContent";
import { apiClient } from "@/lib/api";
import { contentText, type Annotation, type ConfigSlot, type RunOutput } from "@/stores/tukeyStore";

interface Props {
  output: RunOutput;
  slot?: ConfigSlot;
  annotations: Annotation[];
  onChanged: () => Promise<void>;
}

function formatUsage(output: RunOutput): string {
  const usage = output.usage || {};
  const bits = [];
  if (usage.cost != null) bits.push(`$${Number(usage.cost).toFixed(6)}`);
  if (usage.duration_ms != null) bits.push(`${(Number(usage.duration_ms) / 1000).toFixed(1)}s`);
  if (usage.output_tokens != null) bits.push(`${usage.output_tokens} out`);
  return bits.join(" · ");
}

export function RunOutputCard({ output, slot, annotations, onChanged }: Props) {
  const [comment, setComment] = useState("");
  const [annotating, setAnnotating] = useState(false);
  const textBlocks = output.content.filter((block) => block.type === "text");
  const text = output.text || contentText(textBlocks);
  const imageBlocks = output.content.filter((block) => block.type === "image" && block.artifact_id);
  const usage = formatUsage(output);
  const failed = output.status === "failed";

  async function addAnnotation(rating: "positive" | "negative") {
    await apiClient.createRunAnnotation({
      target: { type: "output", run_id: output.run_id, output_id: output.id },
      rating,
      judge: "human",
      comment,
    });
    setComment("");
    setAnnotating(false);
    await onChanged();
  }

  async function copy() {
    const imageUrls = imageBlocks.map((block) => apiClient.artifactContentUrl(block.artifact_id!));
    await navigator.clipboard.writeText(text || imageUrls.join("\n"));
  }

  return (
    <div className="flex h-full min-w-0 flex-col overflow-hidden rounded-md border border-border bg-background">
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-border bg-muted/40 px-3 py-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium" title={slot?.display_name || output.provider_model_id}>
            {slot?.display_name || output.provider_model_id}
          </div>
          <div className="truncate text-[11px] text-muted-foreground">{output.provider_model_id}</div>
        </div>
        <Badge variant={failed ? "destructive" : output.status === "complete" ? "secondary" : "outline"} className="shrink-0">
          {output.status}
        </Badge>
      </div>
      <div className="flex-1 min-h-0 overflow-auto p-3">
        {failed ? (
          <div className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
            {output.error?.message || "Run output failed"}
          </div>
        ) : (
          <>
            {text && <MarkdownContent content={text} />}
            {imageBlocks.length > 0 && (
              <div className={`grid gap-3 ${text ? "mt-3" : ""}`}>
                {imageBlocks.map((block, index) => {
                  const src = apiClient.artifactContentUrl(block.artifact_id!);
                  return (
                    <figure key={`${block.artifact_id}-${index}`} className="overflow-hidden rounded-md border border-border bg-muted/20">
                      <a href={src} target="_blank" rel="noreferrer" title="Open artifact image">
                        <img
                          src={src}
                          alt={block.filename || `Generated image ${index + 1}`}
                          className="max-h-[420px] w-full object-contain"
                          loading="lazy"
                        />
                      </a>
                      <figcaption className="truncate border-t border-border px-2 py-1 text-[11px] text-muted-foreground">
                        {block.filename || block.mime_type || block.artifact_id}
                      </figcaption>
                    </figure>
                  );
                })}
              </div>
            )}
            {!text && imageBlocks.length === 0 && (
              <div className="text-sm text-muted-foreground">No output content</div>
            )}
          </>
        )}
      </div>
      <div className="shrink-0 border-t border-border px-2 py-2">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0 truncate text-xs text-muted-foreground">
            {usage || `response ${output.response_index + 1}`}
            {annotations.length > 0 ? ` · ${annotations.length} notes` : ""}
          </div>
          <div className="flex items-center gap-1">
            <Button size="icon" variant="ghost" className="h-7 w-7" onClick={copy} title="Copy">
              <Copy size={14} />
            </Button>
            <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => setAnnotating((v) => !v)} title="Annotate">
              <MessageSquare size={14} />
            </Button>
          </div>
        </div>
        {annotating && (
          <div className="mt-2 space-y-2">
            <Textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={2}
              className="text-xs"
              placeholder="Add a review note..."
            />
            <div className="flex gap-2">
              <Button size="sm" className="h-7 gap-1.5" onClick={() => addAnnotation("positive")}>
                <Check size={14} /> Good
              </Button>
              <Button size="sm" variant="outline" className="h-7 gap-1.5" onClick={() => addAnnotation("negative")}>
                <X size={14} /> Issue
              </Button>
            </div>
          </div>
        )}
        {annotations.length > 0 && (
          <div className="mt-2 space-y-1">
            {annotations.slice(0, 3).map((annotation) => (
              <div key={annotation.id} className="rounded bg-muted/50 px-2 py-1 text-[11px]">
                <span className="font-medium">{annotation.rating || "note"}:</span>{" "}
                <span className="text-muted-foreground">{annotation.comment || "No comment"}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
