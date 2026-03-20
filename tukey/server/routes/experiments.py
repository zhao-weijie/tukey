"""FastAPI routes for experiment CRUD and execution."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tukey.config import ConfigManager
from tukey.experiment.engine import Experiment
from tukey.storage import Storage

router = APIRouter(prefix="/api/experiments", tags=["experiments"])

_storage: Storage | None = None
_config: ConfigManager | None = None


def init(storage: Storage, config: ConfigManager) -> None:
    global _storage, _config
    _storage = storage
    _config = config


def _get_deps() -> tuple[Storage, ConfigManager]:
    assert _storage and _config
    return _storage, _config


def _get_experiment(experiment_id: str) -> Experiment:
    s, c = _get_deps()
    meta = s.read_experiment_meta(experiment_id)
    if not meta:
        raise HTTPException(404, "Experiment not found")
    return Experiment(s, c, experiment_id)


# --- Pydantic models ---

class ExperimentCreate(BaseModel):
    name: str
    chatroom_id: str
    brief: dict


class ExperimentUpdate(BaseModel):
    name: str | None = None
    brief: dict | None = None


class TestCasesAdd(BaseModel):
    test_cases: list[dict]


class TestCasesReplace(BaseModel):
    test_cases: list[dict]


class AnnotationAdd(BaseModel):
    result_id: str
    verdict: str
    judge: str = "human"
    severity: str | None = None
    notes: str | None = None
    criteria_id: str | None = None


# --- Experiment CRUD ---

@router.post("", status_code=201)
def create_experiment(body: ExperimentCreate):
    s, c = _get_deps()
    # Validate chatroom exists
    cr = s.read_chatroom_meta(body.chatroom_id)
    if not cr:
        raise HTTPException(422, "Chatroom not found")
    exp = Experiment(s, c)
    try:
        return exp.create(body.name, body.chatroom_id, body.brief)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("")
def list_experiments():
    s, _ = _get_deps()
    out = []
    for eid in s.list_experiments():
        meta = s.read_experiment_meta(eid)
        if meta:
            out.append(meta)
    return out


@router.get("/{experiment_id}")
def get_experiment(experiment_id: str):
    exp = _get_experiment(experiment_id)
    return exp.get_meta()


@router.patch("/{experiment_id}")
def update_experiment(experiment_id: str, body: ExperimentUpdate):
    exp = _get_experiment(experiment_id)
    updates = body.model_dump(exclude_none=True)
    try:
        return exp.update_meta(updates)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.delete("/{experiment_id}", status_code=204)
def delete_experiment(experiment_id: str):
    exp = _get_experiment(experiment_id)
    exp.delete()


# --- Test cases ---

@router.post("/{experiment_id}/test-cases", status_code=201)
def add_test_cases(experiment_id: str, body: TestCasesAdd):
    exp = _get_experiment(experiment_id)
    return exp.add_test_cases(body.test_cases)


@router.get("/{experiment_id}/test-cases")
def get_test_cases(experiment_id: str):
    exp = _get_experiment(experiment_id)
    return exp.get_test_cases()


@router.put("/{experiment_id}/test-cases")
def replace_test_cases(experiment_id: str, body: TestCasesReplace):
    exp = _get_experiment(experiment_id)
    return exp.replace_test_cases(body.test_cases)


# --- Runs ---

@router.post("/{experiment_id}/run", status_code=201)
async def run_experiment(experiment_id: str):
    exp = _get_experiment(experiment_id)
    try:
        return await exp.run()
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/{experiment_id}/runs")
def list_runs(experiment_id: str):
    exp = _get_experiment(experiment_id)
    return exp.list_runs()


@router.get("/{experiment_id}/runs/{run_id}")
def get_run(experiment_id: str, run_id: str):
    exp = _get_experiment(experiment_id)
    meta = exp.get_run(run_id)
    if not meta:
        raise HTTPException(404, "Run not found")
    return meta


@router.get("/{experiment_id}/runs/{run_id}/results")
def get_results(experiment_id: str, run_id: str):
    exp = _get_experiment(experiment_id)
    return exp.get_results(run_id)


# --- Annotations ---

@router.post("/{experiment_id}/runs/{run_id}/annotations", status_code=201)
def add_annotation(experiment_id: str, run_id: str, body: AnnotationAdd):
    exp = _get_experiment(experiment_id)
    try:
        return exp.add_annotation(run_id, body.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/{experiment_id}/runs/{run_id}/annotations")
def get_annotations(experiment_id: str, run_id: str):
    exp = _get_experiment(experiment_id)
    return exp.get_annotations(run_id)


# --- Summary ---

@router.get("/{experiment_id}/runs/{run_id}/summary")
def get_run_summary(experiment_id: str, run_id: str):
    exp = _get_experiment(experiment_id)
    return exp.get_run_summary(run_id)
