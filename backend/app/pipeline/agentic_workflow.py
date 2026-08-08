"""Turns a validated ProcessMapVersion into an AgenticWorkflowVersion --
expanded, builder-ready nodes per skills/agentic-workflow-synthesis/SKILL.md.

This module does NOT call an LLM to do the Q1-Q3 classification judgment call
itself (that's real interpretive work, same caution as claim-extraction's
manual-agent-pass approach when no calibrated pipeline exists yet) -- it loads
a structured spec (manually authored today, LLM-authorable later against the
same schema) and VALIDATES it against this app's non-negotiables:

- every node has a real, recognized node_kind
- every edge references a real node
- the escalation-scoping rule is structurally respected (a "deterministic
  decline" edge never routes to a human node; an "agent-judgment adverse"
  edge always routes to a human node, directly or via a gateway)
- every node needing grounding declares BOTH the fabrication and
  misapplication checks, never just one
- every agent_escalation node's confidence trigger carries calibration
  metadata (never a bare, unqualified threshold)
- every claim_refs subject resolves to a real, persisted AtomicClaim

This mirrors process-map-synthesis's validate-before-persist discipline one
layer downstream.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.agentic_workflow import (
    AgenticWorkflowEdge,
    AgenticWorkflowNode,
    AgenticWorkflowVersion,
    NODE_KINDS,
)
from app.models.process_map import ProcessMapVersion

DATA_DIR = Path(__file__).parent.parent.parent / "data"


@dataclass
class AgenticNodeDraft:
    id: str
    node_kind: str
    title: str
    source_task_title: str | None
    claim_refs: list[str]
    spec: dict


@dataclass
class AgenticEdgeDraft:
    from_id: str
    to_id: str
    condition_label: str | None


@dataclass
class AgenticWorkflowDraft:
    process_map_version_label: str
    generator_version: str
    nodes: list[AgenticNodeDraft]
    edges: list[AgenticEdgeDraft]


def load_manual_seed(path: Path | None = None) -> AgenticWorkflowDraft:
    path = path or (DATA_DIR / "aami_agentic_workflow.json")
    raw = json.loads(path.read_text())
    nodes = [
        AgenticNodeDraft(
            id=n["id"], node_kind=n["node_kind"], title=n["title"],
            source_task_title=n.get("source_task_title"),
            claim_refs=n.get("claim_refs", []), spec=n["spec"],
        )
        for n in raw["nodes"]
    ]
    edges = [
        AgenticEdgeDraft(from_id=e["from"], to_id=e["to"], condition_label=e.get("condition_label"))
        for e in raw["edges"]
    ]
    return AgenticWorkflowDraft(
        process_map_version_label=raw["process_map_version_label"],
        generator_version=raw["generator_version"],
        nodes=nodes, edges=edges,
    )


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


_DETERMINISTIC_LABEL_MARKERS = ("deterministic decline",)
_AGENT_ADVERSE_LABEL_MARKERS = ("agent-judgment adverse",)


def validate_agentic_workflow(draft: AgenticWorkflowDraft, known_claim_subjects: set[str] | None = None) -> ValidationResult:
    errors: list[str] = []
    node_by_id = {n.id: n for n in draft.nodes}

    # 1. node_kind is recognized
    for n in draft.nodes:
        if n.node_kind not in NODE_KINDS:
            errors.append(f"node {n.id!r}: unknown node_kind {n.node_kind!r} (must be one of {sorted(NODE_KINDS)})")

    # 2. every edge references a real node
    for e in draft.edges:
        if e.from_id not in node_by_id:
            errors.append(f"edge references unknown from-node {e.from_id!r}")
        if e.to_id not in node_by_id:
            errors.append(f"edge references unknown to-node {e.to_id!r}")

    # 3. escalation scoping rule (see SKILL.md non-negotiables)
    for e in draft.edges:
        label = (e.condition_label or "").lower()
        to_node = node_by_id.get(e.to_id)
        if to_node is None:
            continue
        if any(marker in label for marker in _DETERMINISTIC_LABEL_MARKERS) and to_node.node_kind == "human":
            errors.append(
                f"escalation scoping violation: edge {e.from_id}->{e.to_id} labeled {e.condition_label!r} "
                f"routes a DETERMINISTIC decline to a human node -- deterministic declines must auto-process, "
                f"never a synchronous human hop (see docs/agentic-workflow-design.md §2)"
            )
        if any(marker in label for marker in _AGENT_ADVERSE_LABEL_MARKERS) and to_node.node_kind not in {"human", "gateway"}:
            errors.append(
                f"escalation scoping violation: edge {e.from_id}->{e.to_id} labeled {e.condition_label!r} "
                f"(agent-judgment adverse) must route to a human node (directly or via a gateway), "
                f"not node_kind={to_node.node_kind!r}"
            )

    # 4. grounding: both fabrication + misapplication checks, unless explicitly not applicable
    for n in draft.nodes:
        grounding = n.spec.get("grounding")
        if grounding is None:
            errors.append(f"node {n.id!r}: missing 'grounding' field entirely (must state applicable:false with a reason, or both checks)")
            continue
        if grounding.get("applicable") is False:
            if "reason" not in grounding:
                errors.append(f"node {n.id!r}: grounding.applicable=false but no reason given")
            continue
        if "fabrication_check" not in grounding or "misapplication_check" not in grounding:
            errors.append(
                f"node {n.id!r}: grounding must declare BOTH fabrication_check and misapplication_check "
                f"(one combined 'grounding: yes' is an anti-pattern per SKILL.md) -- got keys {sorted(grounding)}"
            )

    # 5. agent_escalation nodes must carry calibration metadata, not a bare threshold
    required_calibration_fields = {"threshold_set_id", "calibration_dataset_version", "calibration_owner", "revalidation_trigger"}
    for n in draft.nodes:
        if n.node_kind != "agent_escalation":
            continue
        trigger = n.spec.get("confidence_escalation_trigger")
        if not trigger:
            errors.append(f"node {n.id!r}: agent_escalation node missing confidence_escalation_trigger")
            continue
        missing = required_calibration_fields - set(trigger)
        if missing:
            errors.append(f"node {n.id!r}: confidence_escalation_trigger missing calibration fields {sorted(missing)}")

    # 6. every claim_refs subject resolves to a real claim, if a claim set was supplied
    if known_claim_subjects is not None:
        for n in draft.nodes:
            for subject in n.claim_refs:
                if subject not in known_claim_subjects:
                    errors.append(f"node {n.id!r}: claim_refs references unknown claim subject {subject!r}")

    # 7. every non-terminal node has at least one outgoing edge
    terminal_kinds = set()  # no kind is inherently terminal; SVC-03-style terminal nodes are allowed to have
    # a "close"-labeled edge to nowhere further modeled -- check explicitly for presence of *some* outgoing edge
    # OR a downstream_edges spec entry mentioning "close".
    nodes_with_outgoing = {e.from_id for e in draft.edges}
    for n in draft.nodes:
        if n.id in nodes_with_outgoing:
            continue
        downstream = n.spec.get("downstream_edges", [])
        if not any("close" in str(d).lower() for d in downstream):
            errors.append(f"node {n.id!r}: no outgoing edge and no declared terminal ('close') downstream_edges entry")

    return ValidationResult(valid=not errors, errors=errors)


def persist_agentic_workflow(
    db: Session,
    document_id: str,
    process_map_version: ProcessMapVersion,
    draft: AgenticWorkflowDraft,
    claim_id_by_subject: dict[str, str],
) -> AgenticWorkflowVersion:
    """Validates then persists draft as a new AgenticWorkflowVersion tied to
    process_map_version. Refuses to persist an invalid spec -- same
    fail-closed discipline as every other seed step in this app (see
    seed.py's other 'Refusing to seed: ... validation failed' checks)."""
    known_subjects = set(claim_id_by_subject)
    result = validate_agentic_workflow(draft, known_claim_subjects=known_subjects)
    if not result.valid:
        raise RuntimeError("Refusing to persist agentic workflow: validation failed:\n" + "\n".join(result.errors))

    workflow = AgenticWorkflowVersion(
        document_id=document_id,
        process_map_version_id=process_map_version.id,
        process_map_version_label=process_map_version.version_label,
        generator_version=draft.generator_version,
        status="draft",
    )
    db.add(workflow)
    db.flush()

    node_id_map: dict[str, str] = {}
    for n in draft.nodes:
        claim_ids = [claim_id_by_subject[s] for s in n.claim_refs]
        row = AgenticWorkflowNode(
            workflow_id=workflow.id, node_kind=n.node_kind, title=n.title,
            goal=n.spec.get("goal", ""), source_task_title=n.source_task_title,
            spec_json=json.dumps(n.spec), claim_refs=json.dumps(claim_ids),
        )
        db.add(row)
        db.flush()
        node_id_map[n.id] = row.id

    for e in draft.edges:
        db.add(AgenticWorkflowEdge(
            workflow_id=workflow.id,
            from_node_id=node_id_map[e.from_id], to_node_id=node_id_map[e.to_id],
            condition_label=e.condition_label,
        ))

    return workflow
