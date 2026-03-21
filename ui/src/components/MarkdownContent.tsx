import { useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { CopyButton } from "./CopyButton";
import type { ComponentPropsWithoutRef } from "react";
import type { Annotation } from "@/stores/annotationStore";

interface Props {
  content: string;
  annotations?: Annotation[];
  onAnnotationClick?: (annotationId: string, rect: { x: number; y: number }) => void;
}

function CodeBlock({
  className,
  children,
  ...props
}: ComponentPropsWithoutRef<"code">) {
  const isInline = !className && typeof children === "string" && !children.includes("\n");

  if (isInline) {
    return (
      <code className="bg-muted px-1.5 py-0.5 rounded text-sm" {...props}>
        {children}
      </code>
    );
  }

  const text = String(children).replace(/\n$/, "");

  return (
    <div className="group relative">
      <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <CopyButton text={text} size={14} />
      </div>
      <code className={className} {...props}>
        {children}
      </code>
    </div>
  );
}

function findTextNodesIn(node: Node): Text[] {
  const result: Text[] = [];
  const walk = (n: Node) => {
    if (n.nodeType === Node.TEXT_NODE) {
      result.push(n as Text);
    } else {
      n.childNodes.forEach(walk);
    }
  };
  walk(node);
  return result;
}

function highlightText(
  container: HTMLElement,
  exact: string,
  className: string,
  annotationId: string
): void {
  const textNodes = findTextNodesIn(container);
  // Build full text and map each character to its text node + offset
  let fullText = "";
  const charMap: { node: Text; offset: number }[] = [];
  for (const tn of textNodes) {
    const val = tn.nodeValue || "";
    for (let i = 0; i < val.length; i++) {
      charMap.push({ node: tn, offset: i });
    }
    fullText += val;
  }

  const idx = fullText.indexOf(exact);
  if (idx === -1) return;

  const startInfo = charMap[idx];
  const endInfo = charMap[idx + exact.length - 1];
  if (!startInfo || !endInfo) return;

  const range = document.createRange();
  range.setStart(startInfo.node, startInfo.offset);
  range.setEnd(endInfo.node, endInfo.offset + 1);

  const mark = document.createElement("mark");
  mark.className = className;
  mark.dataset.annotationId = annotationId;
  try {
    range.surroundContents(mark);
  } catch {
    // If range crosses element boundaries, wrap what we can
    const fragment = range.extractContents();
    mark.appendChild(fragment);
    range.insertNode(mark);
  }
}

export function MarkdownContent({ content, annotations, onAnnotationClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  const applyHighlights = useCallback(() => {
    const el = containerRef.current;
    if (!el || !annotations || annotations.length === 0) return;

    // Remove existing marks
    el.querySelectorAll("mark[data-annotation-id]").forEach((mark) => {
      const parent = mark.parentNode;
      if (parent) {
        while (mark.firstChild) {
          parent.insertBefore(mark.firstChild, mark);
        }
        parent.removeChild(mark);
        parent.normalize();
      }
    });

    // Apply highlights
    for (const ann of annotations) {
      const className =
        ann.rating === "positive" ? "annotation-positive" : "annotation-negative";
      highlightText(el, ann.exact, className, ann.id);
    }

    // Attach click handlers
    el.querySelectorAll("mark[data-annotation-id]").forEach((mark) => {
      (mark as HTMLElement).onclick = (e) => {
        e.stopPropagation();
        const rect = (mark as HTMLElement).getBoundingClientRect();
        const annId = (mark as HTMLElement).dataset.annotationId!;
        onAnnotationClick?.(annId, {
          x: rect.left + rect.width / 2,
          y: rect.bottom + 4,
        });
      };
    });
  }, [annotations, onAnnotationClick]);

  useEffect(() => {
    // Small delay to let react-markdown finish rendering
    const timer = setTimeout(applyHighlights, 50);
    return () => clearTimeout(timer);
  }, [applyHighlights, content]);

  return (
    <div className="markdown-content text-sm" ref={containerRef}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          code: CodeBlock,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
