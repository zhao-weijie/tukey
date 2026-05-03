"""FastAPI routes for run-native task/use-case organization."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tukey.core import contracts
from tukey.storage import Storage

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

_storage: Storage | None = None


def init(storage: Storage) -> None:
    global _storage
    _storage = storage


def _s() -> Storage:
    assert _storage is not None
    return _storage


class TaskCreate(BaseModel):
    name: str
    description: str | None = None
    tags: list[str] = []
    default_config_set_id: str | None = None


class TaskUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    default_config_set_id: str | None = None
    archived: bool | None = None


@router.get("")
def list_tasks():
    storage = _s()
    tasks = []
    for task_id in storage.list_tasks():
        meta = storage.read_task_meta(task_id)
        if meta:
            tasks.append(meta)
    return tasks


@router.post("", status_code=201)
def create_task(body: TaskCreate):
    storage = _s()
    if body.default_config_set_id:
        config_set = storage.read_config_set_meta(body.default_config_set_id)
        if not config_set:
            raise HTTPException(422, "Default config set not found")
    task = contracts.make_task(body.model_dump())
    storage.write_task_meta(task["id"], task)
    return task


@router.get("/{task_id}")
def get_task(task_id: str):
    task = _s().read_task_meta(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.patch("/{task_id}")
def update_task(task_id: str, body: TaskUpdate):
    storage = _s()
    task = storage.read_task_meta(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    updates = body.model_dump(exclude_unset=True)
    default_config_set_id = updates.get("default_config_set_id")
    if default_config_set_id:
        config_set = storage.read_config_set_meta(default_config_set_id)
        if not config_set:
            raise HTTPException(422, "Default config set not found")
    task.update(updates)
    task["updated_at"] = contracts.utc_now()
    storage.write_task_meta(task_id, task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str):
    storage = _s()
    task = storage.read_task_meta(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    task["archived"] = True
    task["updated_at"] = contracts.utc_now()
    storage.write_task_meta(task_id, task)
