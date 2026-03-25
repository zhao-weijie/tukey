"""Provider protocol — the contract any LLM provider must satisfy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator, Protocol


@dataclass
class LLMResponse:
    content: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float | None = None
    duration_ms: float = 0.0
    tokens_per_sec: float = 0.0
    model: str = ""
    raw_response: dict = field(default_factory=dict)


@dataclass
class ToolCallInfo:
    id: str = ""
    name: str = ""
    arguments: str = ""  # JSON string


@dataclass
class ToolResultInfo:
    tool_call_id: str = ""
    name: str = ""
    result: str = ""
    error: bool = False


@dataclass
class StreamChunk:
    delta: str = ""
    done: bool = False
    response: LLMResponse | None = None  # populated on final chunk
    tool_calls: list[ToolCallInfo] | None = None  # populated when finish_reason == "tool_calls"
    tool_result: ToolResultInfo | None = None  # populated after tool execution


class LLMProvider(Protocol):
    async def complete(
        self,
        messages: list[dict],
        model: str,
        **kwargs,
    ) -> LLMResponse: ...

    async def stream(
        self,
        messages: list[dict],
        model: str,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]: ...
