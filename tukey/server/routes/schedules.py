"""FastAPI routes for run-native schedules."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tukey.core import contracts
from tukey.storage import Storage

router = APIRouter(prefix="/api/schedules", tags=["schedules"])

_storage: Storage | None = None


def init(storage: Storage) -> None:
    global _storage
    _storage = storage


def _s() -> Storage:
    assert _storage is not None
    return _storage


class ScheduleCreate(BaseModel):
    task_id: str | None = None
    eval_plan_id: str | None = None
    config_set_id: str | None = None
    name: str
    status: str = "active"
    cadence: dict = {"type": "manual"}
    model_discovery: dict | None = None


class ScheduleUpdate(BaseModel):
    task_id: str | None = None
    eval_plan_id: str | None = None
    config_set_id: str | None = None
    name: str | None = None
    status: str | None = None
    cadence: dict | None = None
    model_discovery: dict | None = None
    last_run_id: str | None = None


def _require_schedule(storage: Storage, schedule_id: str) -> dict:
    schedule = storage.read_schedule_meta(schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    return schedule


def _validate_refs(storage: Storage, data: dict) -> None:
    if data.get("task_id") and not storage.read_task_meta(data["task_id"]):
        raise HTTPException(422, "Task not found")
    if data.get("eval_plan_id") and not storage.read_eval_plan_meta(data["eval_plan_id"]):
        raise HTTPException(422, "Eval plan not found")
    if data.get("config_set_id") and not storage.read_config_set_meta(data["config_set_id"]):
        raise HTTPException(422, "Config set not found")
    if data.get("last_run_id") and not storage.read_run_record_meta(data["last_run_id"]):
        raise HTTPException(422, "Last run not found")


@router.get("")
def list_schedules():
    storage = _s()
    schedules = []
    for schedule_id in storage.list_schedules():
        schedule = storage.read_schedule_meta(schedule_id)
        if schedule:
            schedules.append(schedule)
    return schedules


@router.post("", status_code=201)
def create_schedule(body: ScheduleCreate):
    storage = _s()
    data = body.model_dump()
    _validate_refs(storage, data)
    schedule = contracts.make_schedule(data)
    storage.write_schedule_meta(schedule["id"], schedule)
    return schedule


@router.get("/{schedule_id}")
def get_schedule(schedule_id: str):
    return _require_schedule(_s(), schedule_id)


@router.patch("/{schedule_id}")
def update_schedule(schedule_id: str, body: ScheduleUpdate):
    storage = _s()
    schedule = _require_schedule(storage, schedule_id)
    updates = body.model_dump(exclude_unset=True)
    _validate_refs(storage, {**schedule, **updates})
    schedule.update(updates)
    schedule["updated_at"] = contracts.utc_now()
    storage.write_schedule_meta(schedule_id, schedule)
    return schedule


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: str):
    storage = _s()
    schedule = _require_schedule(storage, schedule_id)
    schedule["status"] = "paused"
    schedule["updated_at"] = contracts.utc_now()
    storage.write_schedule_meta(schedule_id, schedule)
