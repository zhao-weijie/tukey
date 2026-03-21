import { useState } from "react";
import { ThumbsUp, ThumbsDown } from "@phosphor-icons/react";

interface Props {
  position: { x: number; y: number };
  onSubmit: (rating: "positive" | "negative", comment: string) => void;
  onClose: () => void;
}

export function AnnotationPopover({ position, onSubmit, onClose }: Props) {
  const [rating, setRating] = useState<"positive" | "negative" | null>(null);
  const [comment, setComment] = useState("");

  const handleSubmit = () => {
    if (!rating) return;
    onSubmit(rating, comment);
  };

  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} />
      <div
        data-annotation-popover
        className="fixed z-50 flex flex-col gap-2 rounded-lg bg-popover p-2.5 text-sm text-popover-foreground shadow-md ring-1 ring-foreground/10 w-64"
        style={{
          left: `${position.x}px`,
          top: `${position.y}px`,
          transform: "translateX(-50%)",
        }}
      >
        <div className="flex items-center gap-1">
          <button
            onClick={() => setRating("positive")}
            className={`p-1.5 rounded hover:bg-muted transition-colors ${
              rating === "positive"
                ? "text-green-500 bg-green-500/10"
                : "text-muted-foreground"
            }`}
          >
            <ThumbsUp size={16} weight={rating === "positive" ? "fill" : "regular"} />
          </button>
          <button
            onClick={() => setRating("negative")}
            className={`p-1.5 rounded hover:bg-muted transition-colors ${
              rating === "negative"
                ? "text-red-500 bg-red-500/10"
                : "text-muted-foreground"
            }`}
          >
            <ThumbsDown size={16} weight={rating === "negative" ? "fill" : "regular"} />
          </button>
        </div>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Add a comment..."
          rows={2}
          className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-none"
        />
        <div className="flex justify-end gap-1.5">
          <button
            onClick={onClose}
            className="px-2.5 py-1 rounded text-xs text-muted-foreground hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!rating}
            className="px-2.5 py-1 rounded text-xs bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Save
          </button>
        </div>
      </div>
    </>
  );
}
