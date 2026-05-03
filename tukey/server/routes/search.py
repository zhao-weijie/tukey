"""Search across run-native tasks, chains, runs, outputs, and annotations."""

from __future__ import annotations

from fastapi import APIRouter, Query

from tukey.storage import Storage

router = APIRouter(prefix="/api", tags=["search"])

_storage: Storage | None = None


def init(storage: Storage) -> None:
    global _storage
    _storage = storage


def _snippet(text: str, query: str, width: int = 80) -> str:
    lower = text.lower()
    idx = lower.find(query.lower())
    if idx == -1:
        return text[:width]
    start = max(0, idx - width // 2)
    end = min(len(text), start + width)
    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


@router.get("/search")
def search(q: str = Query(..., min_length=1), limit: int = Query(50, ge=1, le=200)):
    assert _storage is not None
    query_lower = q.lower()
    results: list[dict] = []

    for task_id in _storage.list_tasks():
        if len(results) >= limit:
            break
        task = _storage.read_task_meta(task_id)
        if not task or task.get("archived"):
            continue
        haystack = " ".join([
            task.get("name", ""),
            task.get("description") or "",
            " ".join(task.get("tags", [])),
        ])
        if query_lower in haystack.lower():
            results.append({
                "type": "task",
                "task_id": task_id,
                "task_name": task.get("name", ""),
                "match": "task",
                "snippet": _snippet(haystack, q),
            })

    for chain_id in _storage.list_run_chains():
        if len(results) >= limit:
            break
        chain = _storage.read_run_chain_meta(chain_id)
        if not chain or chain.get("archived"):
            continue
        chain_name = chain.get("name", "")
        if query_lower in chain_name.lower():
            results.append({
                "type": "run_chain",
                "chain_id": chain_id,
                "chain_name": chain_name,
                "match": "chain_name",
                "snippet": _snippet(chain_name, q),
            })

    for run_id in _storage.list_run_records():
        if len(results) >= limit:
            break
        run = _storage.read_run_record_meta(run_id)
        if not run:
            continue
        chain_id = run.get("chain_id")
        chain = _storage.read_run_chain_meta(chain_id) if chain_id else {}
        run_name = run.get("name") or ""
        if run_name and query_lower in run_name.lower():
            results.append({
                "type": "run",
                "run_id": run_id,
                "chain_id": chain_id,
                "chain_name": chain.get("name"),
                "match": "run_name",
                "snippet": _snippet(run_name, q),
            })

        for input_record in _storage.read_run_inputs(run_id):
            if len(results) >= limit:
                break
            content = _content_text(input_record.get("content", []))
            if query_lower in content.lower():
                results.append({
                    "type": "run_input",
                    "run_id": run_id,
                    "input_id": input_record.get("id"),
                    "chain_id": chain_id,
                    "chain_name": chain.get("name"),
                    "match": "input_content",
                    "snippet": _snippet(content, q),
                })

        for output in _storage.read_run_outputs(run_id):
            if len(results) >= limit:
                break
            content = output.get("text") or _content_text(output.get("content", []))
            if query_lower in content.lower():
                results.append({
                    "type": "run_output",
                    "run_id": run_id,
                    "output_id": output.get("id"),
                    "chain_id": chain_id,
                    "chain_name": chain.get("name"),
                    "match": "output_content",
                    "snippet": _snippet(content, q),
                })

        for annotation in _storage.read_run_annotations(run_id):
            if len(results) >= limit:
                break
            comment = annotation.get("comment", "")
            if query_lower in comment.lower():
                results.append({
                    "type": "annotation",
                    "run_id": run_id,
                    "annotation_id": annotation.get("id"),
                    "output_id": annotation.get("target", {}).get("output_id"),
                    "chain_id": chain_id,
                    "chain_name": chain.get("name"),
                    "match": "annotation_comment",
                    "snippet": _snippet(comment, q),
                })

    return {"results": results[:limit]}


def _content_text(content: list[dict]) -> str:
    parts = []
    for block in content or []:
        if block.get("type") == "text":
            parts.append(str(block.get("text", "")))
        elif block.get("type") == "image":
            parts.append(block.get("filename") or block.get("artifact_id") or "[image]")
    return "\n".join(parts)
