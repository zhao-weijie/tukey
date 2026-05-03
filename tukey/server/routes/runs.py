"""FastAPI routes for run-native run records."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tukey.core import contracts
from tukey.storage import Storage

router = APIRouter(prefix="/api/runs", tags=["runs"])

_storage: Storage | None = None


def init(storage: Storage) -> None:
    global _storage
    _storage = storage


def _s() -> Storage:
    assert _storage is not None
    return _storage


class RunCreate(BaseModel):
    name: str | None = None
    status: str = "queued"
    kind: str = "interactive"
    config_set_id: str
    config_version_ids: list[str] = []
    task_id: str | None = None
    eval_plan_id: str | None = None
    schedule_id: str | None = None
    chain_id: str | None = None
    parent_run_ids: list[str] = []
    created_by: str = "user"
    inputs: list[dict] = []
    outputs: list[dict] = []
    events: list[dict] = []


class RunUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    summary: dict | None = None


class RunInputCreate(BaseModel):
    input_index: int | None = None
    role: str = "user"
    content: list[dict]
    test_case_id: str | None = None
    source: dict | None = None


class RunOutputCreate(BaseModel):
    config_version_id: str
    slot_id: str
    provider_model_id: str
    response_index: int = 0
    status: str = "running"
    content: list[dict] = []
    text: str | None = None
    error: dict | None = None
    usage: dict = {}
    raw_response_ref: str | None = None
    tool_interactions: list[dict] | None = None


class RunEventCreate(BaseModel):
    type: str
    data: dict = {}


def _require_run(storage: Storage, run_id: str) -> dict:
    run = storage.read_run_record_meta(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run


def _require_config_set(storage: Storage, config_set_id: str) -> dict:
    config_set = storage.read_config_set_meta(config_set_id)
    if not config_set:
        raise HTTPException(422, "Config set not found")
    return config_set


def _validate_refs(storage: Storage, body: RunCreate) -> None:
    _require_config_set(storage, body.config_set_id)
    known_versions = {
        version["id"]
        for version in storage.read_config_versions(body.config_set_id)
    }
    missing_versions = [
        vid for vid in body.config_version_ids
        if vid not in known_versions
    ]
    if missing_versions:
        raise HTTPException(422, f"Config versions not found: {missing_versions}")
    if body.task_id and not storage.read_task_meta(body.task_id):
        raise HTTPException(422, "Task not found")
    if body.eval_plan_id and not storage.read_eval_plan_meta(body.eval_plan_id):
        raise HTTPException(422, "Eval plan not found")
    if body.schedule_id and not storage.read_schedule_meta(body.schedule_id):
        raise HTTPException(422, "Schedule not found")
    if body.chain_id and not storage.read_run_chain_meta(body.chain_id):
        raise HTTPException(422, "Run chain not found")
    missing_parents = [
        rid for rid in body.parent_run_ids
        if not storage.read_run_record_meta(rid)
    ]
    if missing_parents:
        raise HTTPException(422, f"Parent runs not found: {missing_parents}")


def _append_event(storage: Storage, run_id: str, event: dict) -> dict:
    record = {
        "id": event.get("id", contracts.new_id()),
        "run_id": run_id,
        "type": event["type"],
        "data": event.get("data", {}),
        "created_at": event.get("created_at", contracts.utc_now()),
    }
    storage.append_run_event(run_id, record)
    return record


@router.post("", status_code=201)
def create_run(body: RunCreate):
    storage = _s()
    _validate_refs(storage, body)
    run = contracts.make_run(body.model_dump(exclude={"inputs", "outputs", "events"}))
    storage.write_run_record_meta(run["id"], run)

    for index, input_data in enumerate(body.inputs):
        input_record = dict(input_data)
        input_record.setdefault("input_index", index)
        storage.append_run_input(run["id"], contracts.make_run_input(run["id"], input_record))
    for output_data in body.outputs:
        storage.append_run_output(run["id"], contracts.make_run_output(run["id"], output_data))
    for event_data in body.events:
        _append_event(storage, run["id"], event_data)

    return run


@router.get("")
def list_runs():
    storage = _s()
    runs = []
    for run_id in storage.list_run_records():
        run = storage.read_run_record_meta(run_id)
        if run:
            runs.append(run)
    return runs


@router.get("/{run_id}")
def get_run(run_id: str):
    return _require_run(_s(), run_id)


@router.patch("/{run_id}")
def update_run(run_id: str, body: RunUpdate):
    storage = _s()
    run = _require_run(storage, run_id)
    run.update(body.model_dump(exclude_unset=True))
    storage.write_run_record_meta(run_id, run)
    return run


@router.get("/{run_id}/inputs")
def get_run_inputs(run_id: str):
    storage = _s()
    _require_run(storage, run_id)
    return storage.read_run_inputs(run_id)


@router.post("/{run_id}/inputs", status_code=201)
def append_run_input(run_id: str, body: RunInputCreate):
    storage = _s()
    _require_run(storage, run_id)
    data = body.model_dump(exclude_none=True)
    if data.get("input_index") is None:
        data["input_index"] = len(storage.read_run_inputs(run_id))
    record = contracts.make_run_input(run_id, data)
    storage.append_run_input(run_id, record)
    return record


@router.get("/{run_id}/outputs")
def get_run_outputs(run_id: str):
    storage = _s()
    _require_run(storage, run_id)
    return storage.read_run_outputs(run_id)


@router.post("/{run_id}/outputs", status_code=201)
def append_run_output(run_id: str, body: RunOutputCreate):
    storage = _s()
    run = _require_run(storage, run_id)
    if body.config_version_id not in run.get("config_version_ids", []):
        raise HTTPException(422, "Config version is not part of this run")
    record = contracts.make_run_output(run_id, body.model_dump())
    storage.append_run_output(run_id, record)
    return record


@router.get("/{run_id}/events")
def get_run_events(run_id: str):
    storage = _s()
    _require_run(storage, run_id)
    return storage.read_run_events(run_id)


@router.post("/{run_id}/events", status_code=201)
def append_run_event(run_id: str, body: RunEventCreate):
    storage = _s()
    _require_run(storage, run_id)
    return _append_event(storage, run_id, body.model_dump())


@router.get("/{run_id}/summary")
def get_run_summary(run_id: str):
    storage = _s()
    run = _require_run(storage, run_id)
    outputs = storage.read_run_outputs(run_id)
    return {
        "run_id": run_id,
        "status": run.get("status"),
        "total_inputs": len(storage.read_run_inputs(run_id)),
        "total_outputs": len(outputs),
        "complete_outputs": len([o for o in outputs if o.get("status") == "complete"]),
        "failed_outputs": len([o for o in outputs if o.get("status") == "failed"]),
        "total_events": len(storage.read_run_events(run_id)),
    }
