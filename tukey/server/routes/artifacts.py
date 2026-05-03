"""FastAPI routes for run-native artifact metadata."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tukey.core import contracts
from tukey.storage import Storage

router = APIRouter(prefix="/api", tags=["artifacts"])

_storage: Storage | None = None


def init(storage: Storage) -> None:
    global _storage
    _storage = storage


def _s() -> Storage:
    assert _storage is not None
    return _storage


class ArtifactCreate(BaseModel):
    run_id: str
    output_id: str | None = None
    kind: str
    modality: str
    mime_type: str
    filename: str
    path: str
    size_bytes: int | None = None
    sha256: str | None = None
    metadata: dict = {}


def _find_artifact(storage: Storage, artifact_id: str) -> dict:
    for run_id in storage.list_run_records():
        for artifact in storage.read_artifact_meta(run_id):
            if artifact.get("id") == artifact_id:
                return artifact
    raise HTTPException(404, "Artifact not found")


def _validate_refs(storage: Storage, artifact: dict) -> None:
    run_id = artifact.get("run_id")
    if not run_id or not storage.read_run_record_meta(run_id):
        raise HTTPException(422, "Run not found")
    output_id = artifact.get("output_id")
    if output_id and not any(
        output.get("id") == output_id for output in storage.read_run_outputs(run_id)
    ):
        raise HTTPException(422, "Output not found")


@router.post("/artifacts", status_code=201)
def create_artifact(body: ArtifactCreate):
    storage = _s()
    artifact = contracts.make_artifact(body.model_dump())
    _validate_refs(storage, artifact)
    storage.append_artifact_meta(artifact["run_id"], artifact)
    return artifact


@router.get("/artifacts/{artifact_id}")
def get_artifact(artifact_id: str):
    return _find_artifact(_s(), artifact_id)


@router.get("/runs/{run_id}/artifacts")
def list_run_artifacts(run_id: str):
    storage = _s()
    if not storage.read_run_record_meta(run_id):
        raise HTTPException(404, "Run not found")
    return storage.read_artifact_meta(run_id)
