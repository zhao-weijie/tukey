"""Synthesis tool protocol: the interface any analysis plugin implements."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from tukey.synthesis.bundle import ExperimentBundle


@dataclass
class SynthesisResult:
    """What a tool returns. Deliberately minimal — tools decide what to put here."""

    tool_name: str
    sections: list[Section]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Section:
    """A named block of output. Could be text, a table, a matrix, etc."""

    title: str
    content_type: str  # "text", "table", "matrix", "json"
    body: Any  # str for text, list[list] for table, dict for json, etc.


class SynthesisTool(Protocol):
    """Protocol that synthesis tools implement.

    Tools are simple: they receive an ExperimentBundle and return a SynthesisResult.
    No storage access, no side effects. Pure data in, analysis out.

    Example implementations:
        - BasicStatsTool: word counts, token stats, cost/latency summaries
        - TfIdfTool: vocabulary-level comparison (useful for structured extraction)
        - LlmNarratorTool: send bundle to an LLM, get prose analysis back
        - EmbeddingSimilarityTool: MiniLM-based similarity matrix
    """

    @property
    def name(self) -> str:
        """Short identifier, e.g. 'basic_stats', 'llm_narrator'."""
        ...

    @property
    def description(self) -> str:
        """One-line description of what this tool does."""
        ...

    def analyze(self, bundle: ExperimentBundle) -> SynthesisResult:
        """Run analysis on the experiment bundle. Must not have side effects."""
        ...
