const CONTEXT_LENGTH = 30;

export interface QuoteSelector {
  exact: string;
  prefix: string;
  suffix: string;
}

/**
 * Extract a quote selector from content.
 * Tries raw content first; if not found (e.g. markdown syntax differs from
 * rendered text), falls back to empty prefix/suffix — the exact text is still
 * usable for DOM-based highlight relocation.
 */
export function extractQuoteSelector(
  content: string,
  selectedText: string
): QuoteSelector | null {
  if (!selectedText || !content) return null;

  const idx = content.indexOf(selectedText);
  if (idx === -1) {
    // Selected text comes from rendered DOM and may not appear verbatim
    // in raw markdown (e.g. bold markers stripped). Still return a valid
    // selector — highlights use DOM text matching, not raw markdown.
    return { exact: selectedText, prefix: "", suffix: "" };
  }

  const prefix = content.slice(Math.max(0, idx - CONTEXT_LENGTH), idx);
  const afterIdx = idx + selectedText.length;
  const suffix = content.slice(afterIdx, afterIdx + CONTEXT_LENGTH);

  return { exact: selectedText, prefix, suffix };
}

export function relocateQuote(
  content: string,
  selector: QuoteSelector
): { start: number; end: number } | null {
  if (!selector.exact || !content) return null;

  let searchStart = 0;
  let bestIdx = -1;
  let bestScore = -1;

  while (true) {
    const idx = content.indexOf(selector.exact, searchStart);
    if (idx === -1) break;

    let score = 0;
    if (selector.prefix) {
      const before = content.slice(
        Math.max(0, idx - selector.prefix.length),
        idx
      );
      if (before.endsWith(selector.prefix)) score += 2;
      else if (before.includes(selector.prefix)) score += 1;
    }
    if (selector.suffix) {
      const afterIdx = idx + selector.exact.length;
      const after = content.slice(afterIdx, afterIdx + selector.suffix.length);
      if (after.startsWith(selector.suffix)) score += 2;
      else if (after.includes(selector.suffix)) score += 1;
    }

    if (score > bestScore) {
      bestScore = score;
      bestIdx = idx;
    }

    searchStart = idx + 1;
  }

  if (bestIdx === -1) return null;
  return { start: bestIdx, end: bestIdx + selector.exact.length };
}
