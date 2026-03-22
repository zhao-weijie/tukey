"""Data contract for synthesis: the structured input any tool receives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tukey.storage import Storage


@dataclass
class Exchange:
    """A single turn in a multi-turn test case execution."""

    input: str
    output: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0
    duration_ms: float = 0.0


@dataclass
class Result:
    """One (test_case, model) execution result, with optional annotations."""

    id: str
    test_case_id: str
    model_id: str
    exchanges: list[Exchange]
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost: float = 0.0
    total_duration_ms: float = 0.0
    error: bool = False
    annotations: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ModelSnapshot:
    """Model configuration as it was at run time."""

    id: str
    model_id: str
    display_name: str
    system_prompt: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    provider_id: str | None = None


@dataclass
class ExperimentBundle:
    """Everything a synthesis tool needs. This is the data contract.

    Tools receive this; they never touch Storage directly.
    """

    # Identity
    experiment_id: str
    experiment_name: str
    run_id: str

    # Decision frame
    brief: dict[str, Any]

    # What was tested
    test_cases: list[dict[str, Any]]
    models: list[ModelSnapshot]

    # Results grouped by model_id → list of Result
    results_by_model: dict[str, list[Result]]

    # All results flat (convenience)
    results: list[Result]

    @property
    def model_ids(self) -> list[str]:
        return sorted(self.results_by_model.keys())

    @property
    def model_names(self) -> dict[str, str]:
        return {m.id: m.display_name for m in self.models}

    def responses_for_model(self, model_id: str) -> list[str]:
        """Get all final-turn outputs for a model."""
        return [
            r.exchanges[-1].output
            for r in self.results_by_model.get(model_id, [])
            if r.exchanges and not r.error
        ]


def build_bundle_from_chatroom(
    storage: Storage,
    chatroom_id: str,
) -> ExperimentBundle:
    """Build an ExperimentBundle from a chatroom's fan-out responses.

    This adapts the chatroom message format (user message with multiple model
    responses) into the experiment bundle format so tools work with both.
    """
    import uuid

    meta = storage.read_chatroom_meta(chatroom_id)
    if not meta:
        raise ValueError(f"Chatroom {chatroom_id} not found")

    # Build model snapshots from chatroom config
    models = []
    model_names: dict[str, str] = {}
    for m in meta.get("models", []):
        display = m.get("display_name") or m.get("model_id", m["id"])
        model_names[m["id"]] = display
        models.append(ModelSnapshot(
            id=m["id"],
            model_id=m.get("model_id", m["id"]),
            display_name=display,
            system_prompt=m.get("system_prompt"),
            temperature=m.get("temperature"),
            max_tokens=m.get("max_tokens"),
            provider_id=m.get("provider_id"),
        ))

    # Read all chats and collect responses
    results: list[Result] = []
    results_by_model: dict[str, list[Result]] = {}

    for chat_id in storage.list_chats(chatroom_id):
        messages = storage.read_chat_messages(chatroom_id, chat_id)
        for msg in messages:
            if msg.get("role") != "user":
                continue
            for resp in msg.get("responses", []):
                model_id = resp["model_id"]
                exchange = Exchange(
                    input=msg.get("content", ""),
                    output=resp.get("content", ""),
                    tokens_in=resp.get("tokens_in", 0),
                    tokens_out=resp.get("tokens_out", 0),
                    cost=resp.get("cost") or 0.0,
                    duration_ms=resp.get("duration_ms", 0.0),
                )
                result = Result(
                    id=str(uuid.uuid4()),
                    test_case_id=msg["id"],
                    model_id=model_id,
                    exchanges=[exchange],
                    total_tokens_in=exchange.tokens_in,
                    total_tokens_out=exchange.tokens_out,
                    total_cost=exchange.cost,
                    total_duration_ms=exchange.duration_ms,
                )
                results.append(result)
                results_by_model.setdefault(model_id, []).append(result)

    return ExperimentBundle(
        experiment_id=chatroom_id,
        experiment_name=meta.get("name", chatroom_id),
        run_id="chatroom",
        brief={},
        test_cases=[],
        models=models,
        results_by_model=results_by_model,
        results=results,
    )


def build_bundle(
    storage: Storage,
    experiment_id: str,
    run_id: str,
) -> ExperimentBundle:
    """Build an ExperimentBundle from storage. This is the only place
    that reads from Storage — tools never do."""

    meta = storage.read_experiment_meta(experiment_id)
    if not meta:
        raise ValueError(f"Experiment {experiment_id} not found")

    run_meta = storage.read_run_meta(experiment_id, run_id)
    if not run_meta:
        raise ValueError(f"Run {run_id} not found in experiment {experiment_id}")

    test_cases = storage.read_test_cases(experiment_id)
    raw_results = storage.read_results(experiment_id, run_id)
    raw_annotations = storage.read_annotations(experiment_id, run_id)

    # Index annotations by result_id
    ann_by_result: dict[str, list[dict[str, Any]]] = {}
    for a in raw_annotations:
        ann_by_result.setdefault(a["result_id"], []).append(a)

    # Build model snapshots
    models = []
    for m in run_meta.get("models_snapshot", []):
        models.append(ModelSnapshot(
            id=m["id"],
            model_id=m.get("model_id", m["id"]),
            display_name=m.get("display_name") or m.get("model_id", m["id"]),
            system_prompt=m.get("system_prompt"),
            temperature=m.get("temperature"),
            max_tokens=m.get("max_tokens"),
            provider_id=m.get("provider_id"),
        ))

    # Build results
    results: list[Result] = []
    results_by_model: dict[str, list[Result]] = {}
    for r in raw_results:
        exchanges = [
            Exchange(
                input=e["input"],
                output=e["output"],
                tokens_in=e.get("tokens_in", 0),
                tokens_out=e.get("tokens_out", 0),
                cost=e.get("cost", 0.0),
                duration_ms=e.get("duration_ms", 0.0),
            )
            for e in r.get("exchanges", [])
        ]
        result = Result(
            id=r["id"],
            test_case_id=r["test_case_id"],
            model_id=r["model_id"],
            exchanges=exchanges,
            total_tokens_in=r.get("total_tokens_in", 0),
            total_tokens_out=r.get("total_tokens_out", 0),
            total_cost=r.get("total_cost", 0.0),
            total_duration_ms=r.get("total_duration_ms", 0.0),
            error=r.get("error", False),
            annotations=ann_by_result.get(r["id"], []),
        )
        results.append(result)
        results_by_model.setdefault(r["model_id"], []).append(result)

    return ExperimentBundle(
        experiment_id=experiment_id,
        experiment_name=meta.get("name", ""),
        run_id=run_id,
        brief=meta.get("brief", {}),
        test_cases=test_cases,
        models=models,
        results_by_model=results_by_model,
        results=results,
    )
