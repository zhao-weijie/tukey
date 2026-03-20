import { useRef, useState, useEffect, type ReactNode, Children } from "react";
import { CaretLeft, CaretRight } from "@phosphor-icons/react";

const MIN_CARD_WIDTH = 320;
const GAP = 12;

interface Props {
  children: ReactNode;
}

export function ResponseCarousel({ children }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const childCount = Children.count(children);
  const visibleCount = Math.max(1, Math.floor(containerWidth / MIN_CARD_WIDTH));
  const effectiveVisible = Math.min(visibleCount, childCount);
  const cardWidth = containerWidth > 0
    ? (containerWidth - GAP * (effectiveVisible - 1)) / effectiveVisible
    : MIN_CARD_WIDTH;

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      const w = Math.round(entry.contentRect.width);
      setContainerWidth(prev => Math.abs(prev - w) > 1 ? w : prev);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const updateScrollButtons = () => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 2);
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 2);
  };

  useEffect(() => {
    updateScrollButtons();
  }, [containerWidth, childCount]);

  const scroll = (dir: -1 | 1) => {
    scrollRef.current?.scrollBy({ left: dir * containerWidth, behavior: "smooth" });
  };

  return (
    <div ref={containerRef} className="relative min-w-0 overflow-hidden">
      <div
        ref={scrollRef}
        onScroll={updateScrollButtons}
        className="flex overflow-x-auto scroll-snap-x-mandatory hide-scrollbar"
        style={{ gap: GAP, scrollSnapType: "x mandatory" }}
      >
        {Children.map(children, (child) => (
          <div
            style={{ width: cardWidth, flexShrink: 0, scrollSnapAlign: "start" }}
          >
            {child}
          </div>
        ))}
      </div>
      {canScrollLeft && (
        <button
          onClick={() => scroll(-1)}
          className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1/2 z-10 w-7 h-7 rounded-full bg-background border border-border shadow flex items-center justify-center hover:bg-muted"
        >
          <CaretLeft size={14} />
        </button>
      )}
      {canScrollRight && (
        <button
          onClick={() => scroll(1)}
          className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 z-10 w-7 h-7 rounded-full bg-background border border-border shadow flex items-center justify-center hover:bg-muted"
        >
          <CaretRight size={14} />
        </button>
      )}
    </div>
  );
}
