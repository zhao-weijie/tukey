"""Synthesis CLI: run tools against an experiment or chatroom.

Usage:
    uv run python -m tukey.synthesis.cli <id> [run_id] [--tools tool1,tool2] [--chatroom|--experiment]

Auto-detects whether <id> is a chatroom or experiment.
If run_id is omitted for experiments, uses the latest run.
If --tools is omitted, runs basic_stats only.
Available built-in tools: basic_stats, tfidf
"""

from __future__ import annotations

import sys
import time
from typing import Any

from tukey.storage import Storage
from tukey.synthesis.bundle import build_bundle, build_bundle_from_chatroom
from tukey.synthesis.tool import Section, SynthesisResult, SynthesisTool
from tukey.synthesis.tools.basic_stats import BasicStatsTool
from tukey.synthesis.tools.tfidf import TfIdfTool

# Registry of built-in tools
BUILTIN_TOOLS: dict[str, type] = {
    "basic_stats": BasicStatsTool,
    "tfidf": TfIdfTool,
}


def _print_section(section: Section) -> None:
    """Render a section to the terminal."""
    print(f"\n--- {section.title} ---")

    if section.content_type == "text":
        print(f"  {section.body}")

    elif section.content_type == "table":
        body = section.body
        headers = body["headers"]
        rows = body["rows"]
        # Format cells
        col_widths = [len(str(h)) for h in headers]
        formatted_rows = []
        for row in rows:
            cells = []
            for i, cell in enumerate(row):
                if isinstance(cell, dict) and "mean" in cell:
                    s = f"{cell['mean']:.0f}+/-{cell['stddev']:.0f}"
                else:
                    s = str(cell)
                cells.append(s)
                col_widths[i] = max(col_widths[i], len(s))
            formatted_rows.append(cells)

        header_line = "  ".join(h.rjust(col_widths[i]) for i, h in enumerate(headers))
        print(f"  {header_line}")
        print(f"  {'-' * len(header_line)}")
        for cells in formatted_rows:
            line = "  ".join(c.rjust(col_widths[i]) for i, c in enumerate(cells))
            print(f"  {line}")

    elif section.content_type == "matrix":
        body = section.body
        labels = body["labels"]
        matrix = body["matrix"]
        n = len(labels)
        short = []
        for lb in labels:
            name = lb if isinstance(lb, str) else str(lb)
            if "/" in name:
                name = name.split("/")[-1]
            if len(name) > 16:
                name = name[:14] + ".."
            short.append(name)
        col_w = max(len(s) for s in short) + 1
        header = " " * col_w + "".join(s.rjust(col_w) for s in short)
        print(header)
        for i in range(n):
            row = short[i].rjust(col_w)
            for j in range(n):
                row += f"{matrix[i][j]:.2f}".rjust(col_w)
            print(row)

    elif section.content_type == "json":
        body = section.body
        if isinstance(body, dict):
            for k, v in body.items():
                print(f"  {k}: {v}")
        else:
            print(f"  {body}")


def _print_result(result: SynthesisResult) -> None:
    """Render a full SynthesisResult."""
    print(f"\n{'='*60}")
    print(f"  Tool: {result.tool_name}")
    print(f"{'='*60}")
    for section in result.sections:
        _print_section(section)


def _resolve_tools(tool_names: list[str]) -> list[SynthesisTool]:
    """Resolve tool names to instances."""
    tools: list[SynthesisTool] = []
    for name in tool_names:
        if name in BUILTIN_TOOLS:
            tools.append(BUILTIN_TOOLS[name]())
        else:
            print(f"Warning: unknown tool '{name}', skipping")
    return tools


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    target_id = args[0]
    run_id: str | None = None
    tool_names = ["basic_stats"]
    source = "auto"

    # Parse remaining args
    i = 1
    while i < len(args):
        if args[i] == "--tools" and i + 1 < len(args):
            tool_names = [t.strip() for t in args[i + 1].split(",")]
            i += 2
        elif args[i] == "--chatroom":
            source = "chatroom"
            i += 1
        elif args[i] == "--experiment":
            source = "experiment"
            i += 1
        elif not run_id and not args[i].startswith("--"):
            run_id = args[i]
            i += 1
        else:
            i += 1

    storage = Storage()

    # Auto-detect source: check if it's an experiment or chatroom
    if source == "auto":
        is_experiment = storage.experiment_dir(target_id).exists() and storage.list_runs(target_id)
        is_chatroom = (storage.chatrooms_dir / target_id).exists()
        if is_experiment:
            source = "experiment"
        elif is_chatroom:
            source = "chatroom"
        else:
            print(f"Error: '{target_id}' is not a known experiment or chatroom")
            sys.exit(1)

    # Build bundle
    t0 = time.perf_counter()
    if source == "chatroom":
        bundle = build_bundle_from_chatroom(storage, target_id)
    else:
        if not run_id:
            runs = storage.list_runs(target_id)
            if not runs:
                print(f"Error: no runs found for experiment {target_id}")
                sys.exit(1)
            run_id = runs[-1]
        bundle = build_bundle(storage, target_id, run_id)
    t_bundle = time.perf_counter() - t0

    print(f"Source: {source}")
    print(f"Name: {bundle.experiment_name} ({bundle.experiment_id})")
    print(f"Models: {', '.join(m.display_name for m in bundle.models)}")
    print(f"Results: {len(bundle.results)}")
    print(f"Bundle built in {t_bundle*1000:.1f} ms")

    # Run tools
    tools = _resolve_tools(tool_names)
    for tool in tools:
        t0 = time.perf_counter()
        result = tool.analyze(bundle)
        elapsed = time.perf_counter() - t0
        _print_result(result)
        print(f"\n  ({tool.name} completed in {elapsed*1000:.1f} ms)")


if __name__ == "__main__":
    main()
