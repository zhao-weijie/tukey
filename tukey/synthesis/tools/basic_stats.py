"""Basic per-model statistics: token counts, costs, latency, word/sentence counts.

No dependencies beyond stdlib. Always useful regardless of prompt type.
"""

from __future__ import annotations

import re
import statistics
from typing import Any

from tukey.synthesis.bundle import ExperimentBundle, Result
from tukey.synthesis.tool import Section, SynthesisResult

_SENT_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z"\u201c])')
_WORD_RE = re.compile(r"[a-z]+(?:['\u2019][a-z]+)?")


def _sentences(text: str) -> list[str]:
    parts = _SENT_RE.split(text.strip())
    return [s.strip() for s in parts if s.strip()]


def _words(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall(text.lower()) if len(w) >= 2]


def _agg(vals: list[float | int]) -> dict[str, float]:
    if not vals:
        return {"mean": 0.0, "stddev": 0.0}
    m = statistics.mean(vals)
    s = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return {"mean": round(m, 2), "stddev": round(s, 2)}


class BasicStatsTool:
    """Per-model aggregate statistics. No opinions, just counts."""

    @property
    def name(self) -> str:
        return "basic_stats"

    @property
    def description(self) -> str:
        return "Per-model token counts, costs, latency, and text statistics"

    def analyze(self, bundle: ExperimentBundle) -> SynthesisResult:
        names = bundle.model_names
        rows: list[list[Any]] = []
        headers = [
            "Model", "N", "Tokens Out", "Words", "Sentences",
            "Unique Words", "Cost", "Duration (ms)",
        ]

        for model_id in bundle.model_ids:
            results = bundle.results_by_model[model_id]
            ok = [r for r in results if not r.error]
            outputs = [r.exchanges[-1].output for r in ok if r.exchanges]

            tokens = [r.total_tokens_out for r in ok]
            costs = [r.total_cost for r in ok]
            durations = [r.total_duration_ms for r in ok]
            word_counts = [len(_words(t)) for t in outputs]
            sent_counts = [len(_sentences(t)) for t in outputs]
            unique_counts = [len(set(_words(t))) for t in outputs]

            rows.append([
                names.get(model_id, model_id),
                len(results),
                _agg(tokens),
                _agg(word_counts),
                _agg(sent_counts),
                _agg(unique_counts),
                _agg(costs),
                _agg(durations),
            ])

        # Error summary
        error_counts = {
            names.get(mid, mid): sum(1 for r in rs if r.error)
            for mid, rs in bundle.results_by_model.items()
        }

        # Annotation summary
        ann_summary = self._annotation_summary(bundle)

        sections = [
            Section(title="Per-Model Statistics", content_type="table", body={"headers": headers, "rows": rows}),
        ]

        if any(v > 0 for v in error_counts.values()):
            sections.append(Section(
                title="Errors",
                content_type="json",
                body=error_counts,
            ))

        if ann_summary:
            sections.append(Section(
                title="Annotation Summary",
                content_type="table",
                body=ann_summary,
            ))

        return SynthesisResult(tool_name=self.name, sections=sections)

    def _annotation_summary(self, bundle: ExperimentBundle) -> dict[str, Any] | None:
        """Aggregate annotations per model if any exist."""
        has_any = any(r.annotations for r in bundle.results)
        if not has_any:
            return None

        names = bundle.model_names
        headers = ["Model", "Pass", "Fail", "Partial", "Unannotated"]
        rows = []
        for model_id in bundle.model_ids:
            results = bundle.results_by_model[model_id]
            counts = {"pass": 0, "fail": 0, "partial": 0, "unannotated": 0}
            for r in results:
                if not r.annotations:
                    counts["unannotated"] += 1
                else:
                    for a in r.annotations:
                        v = a.get("verdict", "")
                        if v in counts:
                            counts[v] += 1
            rows.append([
                names.get(model_id, model_id),
                counts["pass"], counts["fail"], counts["partial"], counts["unannotated"],
            ])

        return {"headers": headers, "rows": rows}
