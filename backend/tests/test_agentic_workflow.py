"""Tests for app/pipeline/agentic_workflow.py -- proves the real AAMI spec
(backend/data/aami_agentic_workflow.json) validates cleanly, and that the
validator genuinely catches the non-negotiables from
skills/agentic-workflow-synthesis/SKILL.md, not just always passing."""
from __future__ import annotations

import copy

import pytest

from app.pipeline.agentic_workflow import (
    AgenticEdgeDraft,
    AgenticNodeDraft,
    AgenticWorkflowDraft,
    load_manual_seed,
    validate_agentic_workflow,
)


def _minimal_valid_draft() -> AgenticWorkflowDraft:
    return AgenticWorkflowDraft(
        process_map_version_label="v2",
        generator_version="test",
        nodes=[
            AgenticNodeDraft(
                id="BR-01", node_kind="deterministic", title="Rule check", source_task_title=None,
                claim_refs=["some_subject"],
                spec={"grounding": {"fabrication_check": "x", "misapplication_check": "y"},
                      "downstream_edges": ["pass -> GW-01"]},
            ),
            AgenticNodeDraft(
                id="GW-01", node_kind="gateway", title="Gate", source_task_title=None, claim_refs=[],
                spec={"grounding": {"applicable": False, "reason": "routing only"},
                      "downstream_edges": ["deterministic decline -> SVC-01", "adverse -> HUM-01"]},
            ),
            AgenticNodeDraft(
                id="SVC-01", node_kind="service", title="Close out", source_task_title=None, claim_refs=[],
                spec={"grounding": {"applicable": False, "reason": "no interpretation"},
                      "downstream_edges": ["always -> close"]},
            ),
            AgenticNodeDraft(
                id="HUM-01", node_kind="human", title="Review", source_task_title=None, claim_refs=[],
                spec={"grounding": {"applicable": False, "reason": "human decision, not agent grounding"},
                      "downstream_edges": ["always -> close"]},
            ),
        ],
        edges=[
            AgenticEdgeDraft(from_id="BR-01", to_id="GW-01", condition_label="pass"),
            AgenticEdgeDraft(from_id="GW-01", to_id="SVC-01", condition_label="deterministic decline"),
            AgenticEdgeDraft(from_id="GW-01", to_id="HUM-01", condition_label="agent-judgment adverse"),
        ],
    )


def test_minimal_valid_draft_passes():
    result = validate_agentic_workflow(_minimal_valid_draft(), known_claim_subjects={"some_subject"})
    assert result.valid, result.errors


def test_real_committed_aami_spec_loads_and_validates():
    """Proves the actual data/aami_agentic_workflow.json (what seed.py uses)
    is internally valid -- not a synthetic stand-in."""
    draft = load_manual_seed()
    assert len(draft.nodes) >= 15
    assert len(draft.edges) >= 25

    all_claim_subjects = {subj for n in draft.nodes for subj in n.claim_refs}
    # Validate against itself as the "known" set first (sanity check the file
    # is internally consistent), then separately against the real AAMI claim
    # subjects below (test_seed.py-adjacent integration check).
    result = validate_agentic_workflow(draft, known_claim_subjects=all_claim_subjects)
    assert result.valid, result.errors


def test_real_aami_spec_claim_refs_resolve_to_real_extracted_claims():
    """The claim_refs subjects cited in the workflow spec (e.g. 'driver_impairment',
    'total_loss') must be real subjects from the actual AAMI claim extraction --
    not invented subjects that happen to look plausible."""
    from app.pipeline.extraction import load_manual_seed as load_claims

    claims = load_claims()
    real_subjects = {c.subject for c in claims}

    draft = load_manual_seed()
    result = validate_agentic_workflow(draft, known_claim_subjects=real_subjects)
    assert result.valid, result.errors


# --- RED-BEFORE-GREEN CONTROLS: prove the validator actually catches what it claims to ---

def test_catches_deterministic_decline_routed_to_human():
    draft = _minimal_valid_draft()
    # Break it: point the "deterministic decline" edge at the human node instead of the service node.
    draft.edges = [
        AgenticEdgeDraft(from_id="BR-01", to_id="GW-01", condition_label="pass"),
        AgenticEdgeDraft(from_id="GW-01", to_id="HUM-01", condition_label="deterministic decline"),
    ]
    result = validate_agentic_workflow(draft, known_claim_subjects={"some_subject"})
    assert not result.valid
    assert any("DETERMINISTIC decline to a human node" in e for e in result.errors)


def test_catches_agent_judgment_adverse_not_routed_to_human_or_gateway():
    draft = _minimal_valid_draft()
    draft.edges = [
        AgenticEdgeDraft(from_id="BR-01", to_id="GW-01", condition_label="pass"),
        AgenticEdgeDraft(from_id="GW-01", to_id="SVC-01", condition_label="agent-judgment adverse"),
    ]
    result = validate_agentic_workflow(draft, known_claim_subjects={"some_subject"})
    assert not result.valid
    assert any("agent-judgment adverse" in e for e in result.errors)


def test_catches_missing_misapplication_check():
    draft = _minimal_valid_draft()
    draft.nodes[0].spec["grounding"] = {"fabrication_check": "x"}  # misapplication_check dropped
    result = validate_agentic_workflow(draft, known_claim_subjects={"some_subject"})
    assert not result.valid
    assert any("BOTH fabrication_check and misapplication_check" in e for e in result.errors)


def test_catches_agent_escalation_node_missing_calibration_metadata():
    draft = _minimal_valid_draft()
    draft.nodes.append(
        AgenticNodeDraft(
            id="AG-01", node_kind="agent_escalation", title="Classify", source_task_title=None, claim_refs=[],
            spec={"grounding": {"fabrication_check": "x", "misapplication_check": "y"},
                  "confidence_escalation_trigger": {"threshold_set_id": "v1"},  # missing the other 3 fields
                  "downstream_edges": ["always -> close"]},
        )
    )
    result = validate_agentic_workflow(draft, known_claim_subjects=set())
    assert not result.valid
    assert any("missing calibration fields" in e for e in result.errors)


def test_catches_unknown_claim_subject():
    draft = _minimal_valid_draft()
    draft.nodes[0].claim_refs = ["totally_invented_subject"]
    result = validate_agentic_workflow(draft, known_claim_subjects={"some_subject"})
    assert not result.valid
    assert any("totally_invented_subject" in e for e in result.errors)


def test_catches_dangling_node_with_no_outgoing_edge_and_no_close():
    draft = _minimal_valid_draft()
    draft.nodes.append(
        AgenticNodeDraft(
            id="ORPHAN", node_kind="service", title="Dangling", source_task_title=None, claim_refs=[],
            spec={"grounding": {"applicable": False, "reason": "n/a"}},  # no downstream_edges at all
        )
    )
    result = validate_agentic_workflow(draft, known_claim_subjects={"some_subject"})
    assert not result.valid
    assert any("ORPHAN" in e and "no outgoing edge" in e for e in result.errors)
