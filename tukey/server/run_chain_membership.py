"""Shared helpers for resolving run-chain membership."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from tukey.storage import Storage


def chain_run_ids(storage: Storage, chain_id: str, chain: dict) -> list[str]:
    ids: list[str] = []
    if chain.get("root_run_id"):
        ids.append(chain["root_run_id"])
    for run_id in storage.list_run_records():
        run = storage.read_run_record_meta(run_id)
        if run and run.get("chain_id") == chain_id and run_id not in ids:
            ids.append(run_id)
    for edge in storage.read_run_edges(chain_id):
        for key in ("parent_run_id", "child_run_id"):
            run_id = edge.get(key)
            if run_id and run_id not in ids:
                ids.append(run_id)
    return ids


def run_chain_contexts_by_run_id(
    storage: Storage,
    *,
    include_archived: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()

    for chain_id in storage.list_run_chains():
        chain = storage.read_run_chain_meta(chain_id)
        if not chain or (chain.get("archived") and not include_archived):
            continue
        context = {
            "chain_id": chain_id,
            "chain_name": chain.get("name"),
        }
        for run_id in chain_run_ids(storage, chain_id, chain):
            key = (run_id, chain_id)
            if key in seen:
                continue
            contexts[run_id].append(context)
            seen.add(key)

    return dict(contexts)
