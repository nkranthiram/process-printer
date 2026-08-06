"""Process-map synthesis — see skills/process-map-synthesis/SKILL.md.

Loads a hand-authored (or, in future, LLM-synthesized) task graph, resolves each
task's claim_refs against real extracted claims, and validates DAG structure. The
validator is deterministic code, not a judgment call — this is the "run it, don't
eyeball the diagram" step the skill calls for.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.pipeline.extraction import ClaimDraft

DATA_DIR = Path(__file__).parent.parent.parent / "data"

VALID_NODE_TYPES = {
    "input_required", "eligibility_test", "exclusion_test", "exception_test",
    "evidence_sufficiency_test", "classification", "human_review", "decision",
}
TERMINAL_NODE_TYPES = {"decision", "human_review"}


@dataclass
class TaskDraft:
    id: str
    node_type: str
    title: str
    description: str
    claim_refs: list[str]  # subjects, resolved to claim indices by caller
    position: tuple[float, float]


@dataclass
class EdgeDraft:
    from_id: str
    to_id: str
    label: str


@dataclass
class ProcessMapDraft:
    process_name: str
    tasks: list[TaskDraft]
    edges: list[EdgeDraft]


def load_process_map(path: Path | None = None) -> ProcessMapDraft:
    path = path or (DATA_DIR / "aami_process_map.json")
    raw = json.loads(path.read_text())
    tasks = [
        TaskDraft(
            id=t["id"],
            node_type=t["node_type"],
            title=t["title"],
            description=t["description"],
            claim_refs=t["claim_refs"],
            position=tuple(t["position"]),
        )
        for t in raw["tasks"]
    ]
    edges = [EdgeDraft(from_id=e["from"], to_id=e["to"], label=e["label"]) for e in raw["edges"]]
    return ProcessMapDraft(process_name=raw["process_name"], tasks=tasks, edges=edges)


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors


def validate_claim_refs(process_map: ProcessMapDraft, claims: list[ClaimDraft]) -> ValidationReport:
    """Every claim_ref must resolve to a real claim subject that was actually
    extracted — a dangling reference means a task cites evidence that doesn't
    exist."""
    known_subjects = {c.subject for c in claims}
    report = ValidationReport()
    for task in process_map.tasks:
        for ref in task.claim_refs:
            if ref not in known_subjects:
                report.errors.append(
                    f"task {task.id!r} ({task.title!r}) references unknown claim subject {ref!r}"
                )
    return report


def validate_node_types(process_map: ProcessMapDraft) -> ValidationReport:
    report = ValidationReport()
    for task in process_map.tasks:
        if task.node_type not in VALID_NODE_TYPES:
            report.errors.append(f"task {task.id!r} has invalid node_type {task.node_type!r}")
    return report


def validate_dag_structure(process_map: ProcessMapDraft) -> ValidationReport:
    """No cycles, single reachable start (a node with no incoming edges that
    reaches every other node), every leaf (no outgoing edges) is a terminal
    node_type (decision or human_review) — the process-map-synthesis skill's
    structural contract, checked mechanically rather than by inspection."""
    report = ValidationReport()
    task_ids = {t.id for t in process_map.tasks}
    node_type_by_id = {t.id: t.node_type for t in process_map.tasks}

    adjacency: dict[str, list[str]] = {tid: [] for tid in task_ids}
    incoming: dict[str, int] = {tid: 0 for tid in task_ids}
    for e in process_map.edges:
        if e.from_id not in task_ids:
            report.errors.append(f"edge references unknown from_id {e.from_id!r}")
            continue
        if e.to_id not in task_ids:
            report.errors.append(f"edge references unknown to_id {e.to_id!r}")
            continue
        adjacency[e.from_id].append(e.to_id)
        incoming[e.to_id] += 1

    if report.errors:
        return report  # can't do graph analysis on a graph with dangling edges

    # Cycle detection via DFS coloring — runs over EVERY node regardless of root
    # count, so a cycle is reported even in a graph that also has zero or multiple
    # roots (those are separate, independently-reported problems).
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {tid: WHITE for tid in task_ids}

    def dfs(node: str, stack: list[str]):
        color[node] = GRAY
        stack.append(node)
        for nxt in adjacency[node]:
            if color[nxt] == GRAY:
                cycle = " -> ".join(stack[stack.index(nxt):] + [nxt])
                report.errors.append(f"cycle detected: {cycle}")
            elif color[nxt] == WHITE:
                dfs(nxt, stack)
        stack.pop()
        color[node] = BLACK

    for tid in task_ids:
        if color[tid] == WHITE:
            dfs(tid, [])

    roots = [tid for tid in task_ids if incoming[tid] == 0]
    if len(roots) != 1:
        report.errors.append(f"expected exactly one start node (no incoming edges), found {len(roots)}: {roots}")
    else:
        reached: set[str] = set()

        def collect(node: str):
            if node in reached:
                return
            reached.add(node)
            for nxt in adjacency[node]:
                collect(nxt)

        collect(roots[0])
        unreached = task_ids - reached
        if unreached:
            report.errors.append(f"nodes not reachable from start {roots[0]!r}: {sorted(unreached)}")

    # Leaf (no outgoing edges) must be a terminal node_type.
    for tid in task_ids:
        if not adjacency[tid] and node_type_by_id[tid] not in TERMINAL_NODE_TYPES:
            report.errors.append(
                f"leaf node {tid!r} has node_type {node_type_by_id[tid]!r}, "
                f"not a terminal type {TERMINAL_NODE_TYPES}"
            )

    return report


def validate_process_map(process_map: ProcessMapDraft, claims: list[ClaimDraft]) -> ValidationReport:
    report = ValidationReport()
    for sub_report in (
        validate_node_types(process_map),
        validate_claim_refs(process_map, claims),
        validate_dag_structure(process_map),
    ):
        report.errors.extend(sub_report.errors)
    return report
