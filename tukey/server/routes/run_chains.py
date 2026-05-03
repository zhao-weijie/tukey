"""FastAPI routes for run-chain view state and lineage edges."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tukey.core import contracts
from tukey.server.run_chain_membership import chain_run_ids
from tukey.storage import Storage

router = APIRouter(prefix="/api/run-chains", tags=["run-chains"])

_storage: Storage | None = None


def init(storage: Storage) -> None:
    global _storage
    _storage = storage


def _s() -> Storage:
    assert _storage is not None
    return _storage


class RunChainCreate(BaseModel):
    name: str
    root_run_id: str | None = None
    default_config_set_id: str | None = None


class RunChainUpdate(BaseModel):
    name: str | None = None
    root_run_id: str | None = None
    archived: bool | None = None
    default_config_set_id: str | None = None


class RunEdgeCreate(BaseModel):
    parent_run_id: str
    child_run_id: str
    mapping: dict = {}


class RunChainViewStatePut(BaseModel):
    selected_outputs: dict = {}
    pinned_output_ids: list[str] = []
    collapsed_run_ids: list[str] = []
    visible_slot_ids: list[str] | None = None
    comparison_order: list[str] | None = None


def _require_chain(storage: Storage, chain_id: str) -> dict:
    chain = storage.read_run_chain_meta(chain_id)
    if not chain:
        raise HTTPException(404, "Run chain not found")
    return chain


def _validate_run_ref(storage: Storage, run_id: str, field_name: str) -> None:
    if not storage.read_run_record_meta(run_id):
        raise HTTPException(422, f"{field_name} not found")


def _validate_config_set_ref(storage: Storage, config_set_id: str | None) -> None:
    if config_set_id and not storage.read_config_set_meta(config_set_id):
        raise HTTPException(422, "Default config set not found")


def _validate_edge_outputs(storage: Storage, parent_run_id: str, mapping: dict) -> None:
    parent_output_ids = {
        output["id"] for output in storage.read_run_outputs(parent_run_id)
    }
    missing = []
    for selection in mapping.values():
        output_id = selection.get("output_id")
        if output_id and output_id not in parent_output_ids:
            missing.append(output_id)
    if missing:
        raise HTTPException(422, f"Mapped outputs not found on parent run: {missing}")


def _collect_chain_detail(storage: Storage, chain_id: str) -> dict:
    chain = _require_chain(storage, chain_id)
    run_ids = chain_run_ids(storage, chain_id, chain)
    runs = []
    inputs: dict[str, list[dict]] = {}
    outputs: dict[str, list[dict]] = {}
    events: dict[str, list[dict]] = {}
    annotations: dict[str, list[dict]] = {}
    artifacts: dict[str, list[dict]] = {}
    config_set_ids: set[str] = set()

    for run_id in run_ids:
        run = storage.read_run_record_meta(run_id)
        if not run:
            continue
        runs.append(run)
        if run.get("config_set_id"):
            config_set_ids.add(run["config_set_id"])
        inputs[run_id] = storage.read_run_inputs(run_id)
        outputs[run_id] = storage.read_run_outputs(run_id)
        events[run_id] = storage.read_run_events(run_id)
        annotations[run_id] = storage.read_run_annotations(run_id)
        artifacts[run_id] = storage.read_artifact_meta(run_id)

    if chain.get("default_config_set_id"):
        config_set_ids.add(chain["default_config_set_id"])

    config_sets = []
    config_slots: dict[str, list[dict]] = {}
    config_versions: dict[str, list[dict]] = {}
    for config_set_id in sorted(config_set_ids):
        config_set = storage.read_config_set_meta(config_set_id)
        if not config_set:
            continue
        config_sets.append(config_set)
        config_slots[config_set_id] = storage.read_config_slots(config_set_id)
        config_versions[config_set_id] = storage.read_config_versions(config_set_id)

    return {
        "chain": chain,
        "edges": storage.read_run_edges(chain_id),
        "view_state": storage.read_run_chain_view_state(chain_id),
        "runs": runs,
        "inputs": inputs,
        "outputs": outputs,
        "events": events,
        "annotations": annotations,
        "artifacts": artifacts,
        "config_sets": config_sets,
        "config_slots": config_slots,
        "config_versions": config_versions,
    }


@router.get("")
def list_run_chains():
    storage = _s()
    chains = []
    for chain_id in storage.list_run_chains():
        chain = storage.read_run_chain_meta(chain_id)
        if chain:
            chains.append(chain)
    return chains


@router.post("", status_code=201)
def create_run_chain(body: RunChainCreate):
    storage = _s()
    if body.root_run_id:
        _validate_run_ref(storage, body.root_run_id, "Root run")
    _validate_config_set_ref(storage, body.default_config_set_id)
    chain = contracts.make_run_chain(body.model_dump())
    storage.write_run_chain_meta(chain["id"], chain)
    storage.write_run_chain_view_state(chain["id"], {
        "chain_id": chain["id"],
        "selected_outputs": {},
        "pinned_output_ids": [],
        "collapsed_run_ids": [],
    })
    return chain


@router.get("/{chain_id}")
def get_run_chain(chain_id: str):
    return _require_chain(_s(), chain_id)


@router.get("/{chain_id}/detail")
def get_run_chain_detail(chain_id: str):
    return _collect_chain_detail(_s(), chain_id)


@router.post("/{chain_id}/export")
def export_run_chain(chain_id: str):
    detail = _collect_chain_detail(_s(), chain_id)
    return {
        "schema_version": 1,
        "kind": "tukey.run_chain_export",
        "exported_at": contracts.utc_now(),
        **detail,
    }


@router.patch("/{chain_id}")
def update_run_chain(chain_id: str, body: RunChainUpdate):
    storage = _s()
    chain = _require_chain(storage, chain_id)
    updates = body.model_dump(exclude_unset=True)
    if updates.get("root_run_id"):
        _validate_run_ref(storage, updates["root_run_id"], "Root run")
    if "default_config_set_id" in updates:
        _validate_config_set_ref(storage, updates["default_config_set_id"])
    chain.update(updates)
    chain["updated_at"] = contracts.utc_now()
    storage.write_run_chain_meta(chain_id, chain)
    return chain


@router.get("/{chain_id}/edges")
def get_run_chain_edges(chain_id: str):
    storage = _s()
    _require_chain(storage, chain_id)
    return storage.read_run_edges(chain_id)


@router.post("/{chain_id}/edges", status_code=201)
def create_run_chain_edge(chain_id: str, body: RunEdgeCreate):
    storage = _s()
    _require_chain(storage, chain_id)
    _validate_run_ref(storage, body.parent_run_id, "Parent run")
    _validate_run_ref(storage, body.child_run_id, "Child run")
    _validate_edge_outputs(storage, body.parent_run_id, body.mapping)
    edge = contracts.make_run_edge(chain_id, body.model_dump())
    storage.append_run_edge(chain_id, edge)
    return edge


@router.get("/{chain_id}/view-state")
def get_run_chain_view_state(chain_id: str):
    storage = _s()
    _require_chain(storage, chain_id)
    return storage.read_run_chain_view_state(chain_id)


@router.put("/{chain_id}/view-state")
def put_run_chain_view_state(chain_id: str, body: RunChainViewStatePut):
    storage = _s()
    _require_chain(storage, chain_id)
    state = {"chain_id": chain_id, **body.model_dump(exclude_none=True)}
    storage.write_run_chain_view_state(chain_id, state)
    return state
