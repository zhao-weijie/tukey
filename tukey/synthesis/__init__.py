"""Synthesis: composable analysis tools for experiment and chatroom data.

Public API:
    ExperimentBundle     — the data contract tools receive
    build_bundle         — build from experiment + run
    build_bundle_from_chatroom — build from chatroom fan-out data
    SynthesisTool        — protocol for tool plugins
    SynthesisResult      — what tools return
    Section              — a block of tool output
"""

from tukey.synthesis.bundle import (
    ExperimentBundle,
    Exchange,
    ModelSnapshot,
    Result,
    build_bundle,
    build_bundle_from_chatroom,
)
from tukey.synthesis.tool import Section, SynthesisResult, SynthesisTool

__all__ = [
    "ExperimentBundle",
    "Exchange",
    "ModelSnapshot",
    "Result",
    "build_bundle",
    "build_bundle_from_chatroom",
    "SynthesisTool",
    "SynthesisResult",
    "Section",
]
