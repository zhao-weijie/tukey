"""FastAPI routes for run-native eval plans."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tukey.core import contracts
from tukey.storage import Storage

router = APIRouter(prefix="/api/eval-plans", tags=["eval-plans"])

_storage: Storage | None = None


def init(storage: Storage) -> None:
    global _storage
    _storage = storage


def _s() -> Storage:
    assert _storage is not None
    return _storage


class EvalPlanCreate(BaseModel):
    task_id: str | None = None
    name: str
    version: int = 1
    status: str = "draft"
    brief: dict
    config_set_ids: list[str] = []
    prompt_set_ids: list[str] = []


class EvalPlanUpdate(BaseModel):
    task_id: str | None = None
    name: str | None = None
    version: int | None = None
    status: str | None = None
    brief: dict | None = None
    config_set_ids: list[str] | None = None
    prompt_set_ids: list[str] | None = None


class EvalTestCasesPut(BaseModel):
    test_cases: list[dict]


def _require_eval_plan(storage: Storage, eval_plan_id: str) -> dict:
    plan = storage.read_eval_plan_meta(eval_plan_id)
    if not plan:
        raise HTTPException(404, "Eval plan not found")
    return plan


def _validate_refs(storage: Storage, task_id: str | None, config_set_ids: list[str]) -> None:
    if task_id and not storage.read_task_meta(task_id):
        raise HTTPException(422, "Task not found")
    missing = [
        config_set_id for config_set_id in config_set_ids
        if not storage.read_config_set_meta(config_set_id)
    ]
    if missing:
        raise HTTPException(422, f"Config sets not found: {missing}")


@router.get("")
def list_eval_plans():
    storage = _s()
    plans = []
    for eval_plan_id in storage.list_eval_plans():
        plan = storage.read_eval_plan_meta(eval_plan_id)
        if plan:
            plans.append(plan)
    return plans


@router.post("", status_code=201)
def create_eval_plan(body: EvalPlanCreate):
    storage = _s()
    _validate_refs(storage, body.task_id, body.config_set_ids)
    plan = contracts.make_eval_plan(body.model_dump())
    storage.write_eval_plan_meta(plan["id"], plan)
    return plan


@router.get("/{eval_plan_id}")
def get_eval_plan(eval_plan_id: str):
    return _require_eval_plan(_s(), eval_plan_id)


@router.patch("/{eval_plan_id}")
def update_eval_plan(eval_plan_id: str, body: EvalPlanUpdate):
    storage = _s()
    plan = _require_eval_plan(storage, eval_plan_id)
    updates = body.model_dump(exclude_unset=True)
    _validate_refs(
        storage,
        updates.get("task_id", plan.get("task_id")),
        updates.get("config_set_ids", plan.get("config_set_ids", [])),
    )
    plan.update(updates)
    plan["updated_at"] = contracts.utc_now()
    storage.write_eval_plan_meta(eval_plan_id, plan)
    return plan


@router.post("/{eval_plan_id}/test-cases", status_code=201)
def add_eval_test_cases(eval_plan_id: str, body: EvalTestCasesPut):
    storage = _s()
    _require_eval_plan(storage, eval_plan_id)
    out = []
    for case in body.test_cases:
        record = {
            "id": case.get("id", contracts.new_id()),
            **case,
        }
        storage.append_eval_test_case(eval_plan_id, record)
        out.append(record)
    return out


@router.get("/{eval_plan_id}/test-cases")
def get_eval_test_cases(eval_plan_id: str):
    storage = _s()
    _require_eval_plan(storage, eval_plan_id)
    return storage.read_eval_test_cases(eval_plan_id)


@router.put("/{eval_plan_id}/test-cases")
def put_eval_test_cases(eval_plan_id: str, body: EvalTestCasesPut):
    storage = _s()
    _require_eval_plan(storage, eval_plan_id)
    cases = [
        {"id": case.get("id", contracts.new_id()), **case}
        for case in body.test_cases
    ]
    storage.write_eval_test_cases(eval_plan_id, cases)
    return cases
