import { useState } from "react";
import { Copy, Check } from "@phosphor-icons/react";

interface Props {
  text: string;
  size?: number;
  className?: string;
}

export function CopyButton({ text, size = 16, className = "" }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <button
      onClick={handleCopy}
      className={`p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors ${className}`}
      title={copied ? "Copied!" : "Copy"}
    >
      {copied ? <Check size={size} /> : <Copy size={size} />}
    </button>
  );
}
