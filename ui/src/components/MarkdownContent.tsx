import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { CopyButton } from "./CopyButton";
import type { ComponentPropsWithoutRef } from "react";

interface Props {
  content: string;
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

export function MarkdownContent({ content }: Props) {
  return (
    <div className="markdown-content text-sm">
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
