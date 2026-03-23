import { useState, useCallback, useEffect, useRef } from "react";
import { ChartBar, CaretLeft, CaretRight, ChatText } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { CopyButton } from "./CopyButton";
import { MarkdownContent } from "./MarkdownContent";
import { AnnotationPopover } from "./AnnotationPopover";
import { AnnotationReviewPopover } from "./AnnotationReviewPopover";
import { useAnnotationStore } from "@/stores/annotationStore";
import { extractQuoteSelector } from "@/lib/textSelector";
import type { ResponseMeta } from "@/stores/chatStore";
import type { Annotation } from "@/stores/annotationStore";

interface Props {
  modelName: string;
  responses: ResponseMeta[];
  activeIndex: number;
  onIndexChange: (index: number) => void;
  streaming?: boolean;
  streamingContent?: string;
  streamingTotal?: number;
  messageId?: string;
  chatroomId?: string;
  chatId?: string;
  continuationIndex?: number;
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
  messageId,
  chatroomId,
  chatId,
  continuationIndex,
}: Props) {
  const [showDetails, setShowDetails] = useState(false);
  const [selectionPopover, setSelectionPopover] = useState<{
    position: { x: number; y: number };
    selectedText: string;
  } | null>(null);
  const [reviewPopover, setReviewPopover] = useState<{
    annotation: Annotation;
    position: { x: number; y: number };
  } | null>(null);

  const { annotations, addAnnotation, updateAnnotation, deleteAnnotation } =
    useAnnotationStore();

  // Auto-select first non-error response on initial mount only
  const didAutoSelect = useRef(false);
  useEffect(() => {
    if (streaming || responses.length === 0) return;
    if (didAutoSelect.current) return;
    didAutoSelect.current = true;
    if (responses[activeIndex]?.error) {
      const betterIdx = responses.findIndex(r => !r.error);
      if (betterIdx !== -1 && betterIdx !== activeIndex) {
        onIndexChange(betterIdx);
      }
    }
  }, [responses]); // eslint-disable-line react-hooks/exhaustive-deps

  const active = responses[activeIndex];
  const content = streaming ? (streamingContent ?? "") : (active?.content ?? "");
  const error = active?.error;
  const metadata = streaming ? undefined : active;
  const err = error ? friendlyError(content) : null;
  const isContinuation = continuationIndex != null && activeIndex === continuationIndex;

  // Get annotations for this specific response
  const chatAnnotations = chatId ? annotations[chatId] || [] : [];
  const responseAnnotations = chatAnnotations.filter(
    (a) =>
      a.target.source.message_id === messageId &&
      a.target.source.model_id === active?.model_id &&
      a.target.source.response_index === activeIndex
  );

  const handleMouseUp = useCallback((e: React.MouseEvent) => {
    if (streaming || !messageId || !chatroomId || !chatId) return;
    // Don't trigger when clicking inside annotation popover
    if ((e.target as HTMLElement).closest("[data-annotation-popover]")) return;

    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return;

    const selectedText = selection.toString().trim();
    if (!selectedText) return;

    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();

    setSelectionPopover({
      position: { x: rect.left + rect.width / 2, y: rect.bottom + 4 },
      selectedText,
    });
  }, [streaming, messageId, chatroomId, chatId]);

  const handleAnnotationSubmit = async (
    rating: "positive" | "negative",
    comment: string
  ) => {
    if (!selectionPopover || !chatroomId || !chatId || !messageId || !active)
      return;

    const selector = extractQuoteSelector(content, selectionPopover.selectedText);
    if (!selector) return;

    await addAnnotation(chatroomId, chatId, {
      target: {
        source: {
          message_id: messageId,
          model_id: active.model_id,
          response_index: activeIndex,
        },
        selector: {
          type: "TextQuoteSelector" as const,
          ...selector,
        },
      },
      rating,
      comment,
    });

    setSelectionPopover(null);
    window.getSelection()?.removeAllRanges();
  };

  const handleAnnotationClick = useCallback(
    (annotationId: string, rect: { x: number; y: number }) => {
      const ann = responseAnnotations.find((a) => a.id === annotationId);
      if (ann) {
        setReviewPopover({ annotation: ann, position: rect });
      }
    },
    [responseAnnotations]
  );

  const handleAnnotationUpdate = async (data: {
    rating?: string;
    comment?: string;
  }) => {
    if (!reviewPopover || !chatroomId || !chatId) return;
    await updateAnnotation(chatroomId, chatId, reviewPopover.annotation.id, data);
    setReviewPopover(null);
  };

  const handleAnnotationDelete = async () => {
    if (!reviewPopover || !chatroomId || !chatId) return;
    await deleteAnnotation(chatroomId, chatId, reviewPopover.annotation.id);
    setReviewPopover(null);
  };

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
          <span className={cn("text-sm truncate", isContinuation ? "font-semibold" : "font-medium")} title={modelName}>{modelName}</span>
          {streaming && (
            <Badge variant="secondary" className="text-xs animate-pulse">
              {streamingTotal && streamingTotal > 1
                ? `streaming 1/${streamingTotal}...`
                : "streaming..."}
            </Badge>
          )}
        </div>
        <div className="p-3" onMouseUp={handleMouseUp}>
          {streaming && !content ? (
            <div className="space-y-2 animate-pulse">
              <div className="h-3 w-full bg-muted rounded" />
              <div className="h-3 w-3/4 bg-muted rounded" />
              <div className="h-3 w-1/2 bg-muted rounded" />
            </div>
          ) : err ? (
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
            <MarkdownContent
              content={content || (streaming ? "" : "No response")}
              annotations={responseAnnotations}
              onAnnotationClick={handleAnnotationClick}
            />
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
            {responseAnnotations.length > 0 && (
              <Tooltip>
                <TooltipTrigger className="flex items-center gap-1 p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
                  <ChatText size={14} />
                  <span className="text-xs tabular-nums">{responseAnnotations.length}</span>
                </TooltipTrigger>
                <TooltipContent side="top">
                  {responseAnnotations.length} annotation{responseAnnotations.length !== 1 ? "s" : ""}
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
                <span className={cn("text-xs tabular-nums", isContinuation ? "font-semibold text-foreground" : "text-muted-foreground")}>
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

      {/* Selection popover for creating annotations */}
      {selectionPopover && (
        <AnnotationPopover
          position={selectionPopover.position}
          onSubmit={handleAnnotationSubmit}
          onClose={() => setSelectionPopover(null)}
        />
      )}

      {/* Review popover for existing annotations */}
      {reviewPopover && (
        <AnnotationReviewPopover
          annotation={reviewPopover.annotation}
          anchorRect={reviewPopover.position}
          onUpdate={handleAnnotationUpdate}
          onDelete={handleAnnotationDelete}
          onClose={() => setReviewPopover(null)}
        />
      )}
    </div>
  );
}
