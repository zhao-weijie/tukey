"""FastAPI routes for unified run-native annotations."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from tukey.core import contracts
from tukey.storage import Storage

router = APIRouter(prefix="/api/annotations", tags=["annotations"])

_storage: Storage | None = None


def init(storage: Storage) -> None:
    global _storage
    _storage = storage


def _s() -> Storage:
    assert _storage is not None
    return _storage


class AnnotationCreate(BaseModel):
    target: dict
    rating: str | None = None
    severity: str | None = None
    criteria_id: str | None = None
    judge: str = "human"
    comment: str = ""


class AnnotationUpdate(BaseModel):
    target: dict | None = None
    rating: str | None = None
    severity: str | None = None
    criteria_id: str | None = None
    judge: str | None = None
    comment: str | None = None


def _target_run_id(target: dict) -> str:
    run_id = target.get("run_id")
    if not run_id and target.get("output_id"):
        for candidate_run_id in _s().list_run_records():
            outputs = _s().read_run_outputs(candidate_run_id)
            if any(output.get("id") == target["output_id"] for output in outputs):
                run_id = candidate_run_id
                break
    if not run_id:
        raise HTTPException(422, "Annotation target must include run_id or known output_id")
    return run_id


def _validate_target(storage: Storage, target: dict) -> str:
    run_id = _target_run_id(target)
    if not storage.read_run_record_meta(run_id):
        raise HTTPException(422, "Target run not found")
    output_id = target.get("output_id")
    if output_id and not any(
        output.get("id") == output_id for output in storage.read_run_outputs(run_id)
    ):
        raise HTTPException(422, "Target output not found")
    return run_id


def _find_annotation(storage: Storage, annotation_id: str) -> tuple[str, list[dict], dict]:
    for run_id in storage.list_run_records():
        annotations = storage.read_run_annotations(run_id)
        for annotation in annotations:
            if annotation.get("id") == annotation_id:
                return run_id, annotations, annotation
    raise HTTPException(404, "Annotation not found")


@router.get("")
def list_annotations(
    run_id: str | None = Query(default=None),
    output_id: str | None = Query(default=None),
):
    storage = _s()
    run_ids = [run_id] if run_id else storage.list_run_records()
    annotations = []
    for rid in run_ids:
        if not storage.read_run_record_meta(rid):
            continue
        for annotation in storage.read_run_annotations(rid):
            target = annotation.get("target", {})
            if output_id and target.get("output_id") != output_id:
                continue
            annotations.append(annotation)
    return annotations


@router.post("", status_code=201)
def create_annotation(body: AnnotationCreate):
    storage = _s()
    annotation = contracts.make_annotation(body.model_dump())
    run_id = _validate_target(storage, annotation["target"])
    storage.append_run_annotation(run_id, annotation)
    return annotation


@router.patch("/{annotation_id}")
def update_annotation(annotation_id: str, body: AnnotationUpdate):
    storage = _s()
    run_id, annotations, annotation = _find_annotation(storage, annotation_id)
    updates = body.model_dump(exclude_unset=True)
    if "target" in updates:
        new_run_id = _validate_target(storage, updates["target"])
        if new_run_id != run_id:
            raise HTTPException(422, "Moving annotations across runs is not supported")
    annotation.update(updates)
    annotation["updated_at"] = contracts.utc_now()
    storage.write_jsonl(storage.run_record_dir(run_id) / "annotations.jsonl", annotations)
    return annotation


@router.delete("/{annotation_id}", status_code=204)
def delete_annotation(annotation_id: str):
    storage = _s()
    run_id, annotations, _ = _find_annotation(storage, annotation_id)
    updated = [a for a in annotations if a.get("id") != annotation_id]
    storage.write_jsonl(storage.run_record_dir(run_id) / "annotations.jsonl", updated)
