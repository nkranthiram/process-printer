"""Scenario validation — see skills/scenario-validation/SKILL.md.

Loads manually-traced claim scenarios and mechanically checks each traced_path is a
real path through the process map DAG (every consecutive pair is a real edge,
starts at the single start node, ends at a terminal node).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.pipeline.synthesis import ProcessMapDraft, TERMINAL_NODE_TYPES

DATA_DIR = Path(__file__).parent.parent.parent / "data"


@dataclass
class ValidationCaseDraft:
    scenario_name: str
    claim_description: str
    expected_outcome: str
    traced_path: list[str]
    actual_outcome: str
    result: str
    notes: str | None = None


def load_manual_validation_cases(path: Path | None = None) -> list[ValidationCaseDraft]:
    path = path or (DATA_DIR / "aami_validation_cases.json")
    raw = json.loads(path.read_text())
    return [
        ValidationCaseDraft(
            scenario_name=c["scenario_name"], claim_description=c["claim_description"],
            expected_outcome=c["expected_outcome"], traced_path=c["traced_path"],
            actual_outcome=c["actual_outcome"], result=c["result"], notes=c.get("notes"),
        )
        for c in raw
    ]


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors


def validate_traced_paths(cases: list[ValidationCaseDraft], process_map: ProcessMapDraft) -> ValidationReport:
    """Every scenario's traced_path must be a REAL path through the map: each
    consecutive pair a real edge, starting at the map's single start node, ending
    at a terminal node_type. This is what stops a scenario's narrative from
    quietly drifting away from what the map actually encodes."""
    report = ValidationReport()

    task_ids = {t.id for t in process_map.tasks}
    node_type_by_id = {t.id: t.node_type for t in process_map.tasks}
    real_edges = {(e.from_id, e.to_id) for e in process_map.edges}
    incoming = {tid: 0 for tid in task_ids}
    for e in process_map.edges:
        incoming[e.to_id] = incoming.get(e.to_id, 0) + 1
    start_candidates = [tid for tid in task_ids if incoming.get(tid, 0) == 0]
    start_id = start_candidates[0] if len(start_candidates) == 1 else None

    for case in cases:
        path = case.traced_path
        if not path:
            report.errors.append(f"{case.scenario_name!r}: empty traced_path")
            continue
        for tid in path:
            if tid not in task_ids:
                report.errors.append(f"{case.scenario_name!r}: traced_path references unknown task {tid!r}")
        if any(tid not in task_ids for tid in path):
            continue  # can't check edges against unknown tasks

        if start_id is not None and path[0] != start_id:
            report.errors.append(
                f"{case.scenario_name!r}: traced_path starts at {path[0]!r}, expected start node {start_id!r}"
            )

        for a, b in zip(path, path[1:]):
            if (a, b) not in real_edges:
                report.errors.append(f"{case.scenario_name!r}: no real edge {a!r} -> {b!r} in the process map")

        last = path[-1]
        if node_type_by_id.get(last) not in TERMINAL_NODE_TYPES:
            report.errors.append(
                f"{case.scenario_name!r}: traced_path ends at {last!r} "
                f"(node_type {node_type_by_id.get(last)!r}), not a terminal node"
            )

        if case.result not in {"pass", "fail"}:
            report.errors.append(f"{case.scenario_name!r}: result must be 'pass' or 'fail', got {case.result!r}")

    return report
