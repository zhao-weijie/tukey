import { useState } from "react";
import { ThumbsUp, ThumbsDown, PencilSimple, Trash } from "@phosphor-icons/react";
import type { Annotation } from "@/stores/annotationStore";

interface Props {
  annotation: Annotation;
  anchorRect: { x: number; y: number };
  onUpdate: (data: { rating?: string; comment?: string }) => void;
  onDelete: () => void;
  onClose: () => void;
}

export function AnnotationReviewPopover({
  annotation,
  anchorRect,
  onUpdate,
  onDelete,
  onClose,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [rating, setRating] = useState(annotation.rating);
  const [comment, setComment] = useState(annotation.comment);

  const handleSave = () => {
    onUpdate({ rating, comment });
    setEditing(false);
  };

  const handleDelete = () => {
    onDelete();
  };

  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} />
      <div
        className="fixed z-50 flex flex-col gap-2 rounded-lg bg-popover p-2.5 text-sm text-popover-foreground shadow-md ring-1 ring-foreground/10 w-64"
        style={{
          left: `${anchorRect.x}px`,
          top: `${anchorRect.y}px`,
          transform: "translateX(-50%)",
        }}
      >
        {editing ? (
          <>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setRating("positive")}
                className={`p-1.5 rounded hover:bg-muted transition-colors ${
                  rating === "positive"
                    ? "text-green-500 bg-green-500/10"
                    : "text-muted-foreground"
                }`}
              >
                <ThumbsUp
                  size={16}
                  weight={rating === "positive" ? "fill" : "regular"}
                />
              </button>
              <button
                onClick={() => setRating("negative")}
                className={`p-1.5 rounded hover:bg-muted transition-colors ${
                  rating === "negative"
                    ? "text-red-500 bg-red-500/10"
                    : "text-muted-foreground"
                }`}
              >
                <ThumbsDown
                  size={16}
                  weight={rating === "negative" ? "fill" : "regular"}
                />
              </button>
            </div>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={2}
              className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-none"
            />
            <div className="flex justify-end gap-1.5">
              <button
                onClick={() => setEditing(false)}
                className="px-2.5 py-1 rounded text-xs text-muted-foreground hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="px-2.5 py-1 rounded text-xs bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                Save
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                {annotation.rating === "positive" ? (
                  <ThumbsUp size={16} weight="fill" className="text-green-500" />
                ) : (
                  <ThumbsDown size={16} weight="fill" className="text-red-500" />
                )}
                <span className="text-xs text-muted-foreground capitalize">
                  {annotation.rating}
                </span>
              </div>
              <div className="flex items-center gap-0.5">
                <button
                  onClick={() => setEditing(true)}
                  className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                >
                  <PencilSimple size={14} />
                </button>
                <button
                  onClick={handleDelete}
                  className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-destructive transition-colors"
                >
                  <Trash size={14} />
                </button>
              </div>
            </div>
            {annotation.comment && (
              <p className="text-xs text-foreground/80">{annotation.comment}</p>
            )}
          </>
        )}
      </div>
    </>
  );
}
